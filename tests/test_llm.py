import json
from urllib.error import HTTPError

import pytest

from src.llm.client import Client, ModelConfig
from src.schemas import report_schema


def envelope(content, model='fixture-model'):
    return {'id': 'response-id', 'model': model, 'system_fingerprint': 'fp-test',
            'choices': [{'finish_reason': 'stop', 'message': {'content': content, 'refusal': None}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


VALID = json.dumps({'prediction': 'Fallacious', 'confidence': 0.8, 'content': 'Evidence.'})


class Transport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def complete(self, payload):
        self.requests.append(payload)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def call(client, **meta):
    return client.generate(system_prompt='Analyze.', user_prompt='{"input":"hello"}',
                           schema=report_schema('detection'),
                           metadata={'dataset': 'hash', 'split': 'dev', 'task': 'detection',
                                     'sample_id': '1', 'role': 'Factual', 'protocol': 'none', **meta})


def make_client(tmp_path, transport, **options):
    return Client(ModelConfig(name='fixture-model', backoff_seconds=0, **options),
                  tmp_path / 'cache.sqlite', tmp_path / 'raw.jsonl', transport=transport)


def test_invalid_output_is_audited_retried_and_cached(tmp_path):
    transport = Transport([envelope('not json'), envelope(VALID)])
    client = make_client(tmp_path, transport)
    assert call(client)['prediction'] == 'Fallacious'
    assert client.usage['prompt_tokens'] == 20
    assert client.usage['completion_tokens'] == 10
    assert call(client)['prediction'] == 'Fallacious'
    assert client.usage['prompt_tokens'] == 20  # cache does not rebill
    assert client.usage['cache_hits'] == 1
    logs = [json.loads(line) for line in (tmp_path / 'raw.jsonl').read_text().splitlines()]
    assert logs[0]['response']['choices'][0]['message']['content'] == 'not json'
    assert logs[0]['valid'] is False
    assert logs[1]['valid'] is True
    assert 'tools' not in transport.requests[0]
    assert transport.requests[0]['response_format']['json_schema']['strict'] is True


def test_cache_isolates_task_role_sample_and_temperature(tmp_path):
    transport = Transport([envelope(VALID)] * 4)
    client = make_client(tmp_path, transport)
    call(client)
    call(client, role='Logical')
    call(client, sample_id='2')
    other = make_client(tmp_path, transport, temperature=0.5)
    call(other)
    assert len(transport.requests) == 4


def test_transient_failure_retried_but_auth_error_not_retried(tmp_path):
    transient = HTTPError('https://example.invalid', 429, 'rate limit', {}, None)
    transport = Transport([transient, envelope(VALID)])
    client = make_client(tmp_path, transport)
    assert call(client)['prediction'] == 'Fallacious'
    assert client.usage['api_calls'] == 2
    auth = Transport([HTTPError('https://example.invalid', 401, 'unauthorized', {}, None)])
    client = make_client(tmp_path, auth)
    with pytest.raises(HTTPError):
        call(client, sample_id='uncached')
    assert len(auth.requests) == 1


def test_persistent_invalid_response_fails_without_fake_label(tmp_path):
    client = make_client(tmp_path, Transport([envelope('{}')] * 2), max_attempts=2)
    with pytest.raises(ValueError, match='valid'):
        call(client)
    assert client.usage['api_calls'] == 2


def test_truncated_response_is_not_accepted_even_if_json_valid(tmp_path):
    response = envelope(VALID)
    response['choices'][0]['finish_reason'] = 'length'
    client = make_client(tmp_path, Transport([response]), max_attempts=1)
    with pytest.raises(ValueError):
        call(client)


def test_nan_confidence_is_rejected(tmp_path):
    raw = '{"prediction":"Fallacious","confidence":NaN,"content":"x"}'
    client = make_client(tmp_path, Transport([envelope(raw)]), max_attempts=1)
    with pytest.raises(ValueError):
        call(client)


@pytest.mark.parametrize('usage', [{}, {'prompt_tokens': 10},
    {'prompt_tokens': -10, 'completion_tokens': 5, 'total_tokens': -5}])
def test_incomplete_or_invalid_usage_makes_cost_unknown(tmp_path, usage):
    response = envelope(VALID)
    response['usage'] = usage
    client = make_client(tmp_path, Transport([response]), input_cost_per_million=1, output_cost_per_million=2)
    call(client)
    assert client.estimated_cost() is None
    assert client.usage['missing_usage_responses'] == 1


def test_http_error_audit_preserves_provider_diagnostics(tmp_path):
    from io import BytesIO
    error = HTTPError('https://example.invalid', 400, 'bad request', {'x-request-id': 'req-123'},
                      BytesIO(b'{"error":{"message":"Unsupported schema"}}'))
    client = make_client(tmp_path, Transport([error]))
    with pytest.raises(HTTPError):
        call(client)
    event = json.loads((tmp_path / 'raw.jsonl').read_text())
    assert event['http_error_body'] == '{"error":{"message":"Unsupported schema"}}'
    assert event['request_id'] == 'req-123'


def test_real_transport_constructs_authenticated_request_without_tools(monkeypatch):
    from src.llm.openai_client import OpenAITransport
    from io import BytesIO
    seen = []

    def urlopen(request, timeout):
        seen.append((request, timeout))
        return BytesIO(json.dumps(envelope(VALID)).encode('utf-8'))

    monkeypatch.setenv('TEST_API_KEY', 'fixture-key')
    monkeypatch.setattr('src.llm.openai_client.urlopen', urlopen)
    transport = OpenAITransport(ModelConfig(name='fixture', api_key_env='TEST_API_KEY', timeout_seconds=12))
    payload = {'model': 'fixture', 'messages': [{'role': 'user', 'content': 'sample'}]}
    assert transport.complete(payload)['model'] == 'fixture-model'
    request, timeout = seen[0]
    assert request.full_url == 'https://api.openai.com/v1/chat/completions'
    assert request.get_header('Authorization') == 'Bearer fixture-key'
    assert json.loads(request.data) == payload
    assert timeout == 12


def test_no_api_key_fails_before_network(monkeypatch):
    from src.llm.openai_client import OpenAITransport
    monkeypatch.delenv('MISSING_TEST_KEY', raising=False)
    with pytest.raises(RuntimeError, match='MISSING_TEST_KEY'):
        OpenAITransport(ModelConfig(name='fixture', api_key_env='MISSING_TEST_KEY')).complete({})
