import json
from io import BytesIO

import pytest

from src.llm.client import Client
from src.llm.config import ModelConfig
from src.schemas import report_schema


VALID = json.dumps({
    'prediction': 'Fallacious',
    'confidence': 0.8,
    'content': 'Evidence.',
})


def gemini_envelope(content=VALID):
    return {
        'responseId': 'gemini-response-id',
        'modelVersion': 'gemini-2.5-flash',
        'candidates': [{
            'content': {
                'role': 'model',
                'parts': [{'text': content}],
            },
            'finishReason': 'STOP',
        }],
        'usageMetadata': {
            'promptTokenCount': 10,
            'candidatesTokenCount': 5,
            'totalTokenCount': 15,
        },
    }


def test_model_config_accepts_gemini_provider():
    config = ModelConfig(
        name='gemini-2.5-flash',
        provider='gemini',
        base_url='https://generativelanguage.googleapis.com/v1beta',
        api_key_env='TEST_GEMINI_API_KEY',
    )

    assert config.provider == 'gemini'


def test_client_selects_gemini_transport(tmp_path):
    client = Client(
        ModelConfig(
            name='gemini-2.5-flash',
            provider='gemini',
            base_url='https://generativelanguage.googleapis.com/v1beta',
        ),
        tmp_path / 'cache.sqlite',
        tmp_path / 'raw.jsonl',
    )

    assert type(client.transport).__name__ == 'GeminiTransport'


def test_gemini_transport_maps_request_and_normalizes_response(monkeypatch):
    from src.llm.gemini_client import GeminiTransport

    seen = []

    def urlopen(request, timeout):
        seen.append((request, timeout))
        return BytesIO(json.dumps(gemini_envelope()).encode('utf-8'))

    monkeypatch.setenv('TEST_GEMINI_API_KEY', 'fixture-gemini-key')
    monkeypatch.setattr('src.llm.gemini_client.urlopen', urlopen)
    config = ModelConfig(
        name='gemini-2.5-flash',
        provider='gemini',
        base_url='https://generativelanguage.googleapis.com/v1beta',
        api_key_env='TEST_GEMINI_API_KEY',
        temperature=0.2,
        max_completion_tokens=128,
        timeout_seconds=12,
    )
    transport = GeminiTransport(config)
    schema = report_schema('detection')
    payload = {
        'model': config.name,
        'messages': [
            {'role': 'system', 'content': 'Analyze the supplied text.'},
            {'role': 'user', 'content': 'Return the requested JSON.'},
        ],
        'temperature': 0.2,
        'max_completion_tokens': 128,
        'response_format': {
            'type': 'json_schema',
            'json_schema': {'schema': schema},
        },
    }

    result = transport.complete(payload)

    assert result['id'] == 'gemini-response-id'
    assert result['model'] == 'gemini-2.5-flash'
    assert result['choices'][0]['finish_reason'] == 'stop'
    assert json.loads(result['choices'][0]['message']['content']) == json.loads(VALID)
    assert result['usage'] == {
        'prompt_tokens': 10,
        'completion_tokens': 5,
        'total_tokens': 15,
    }

    request, timeout = seen[0]
    assert request.full_url == (
        'https://generativelanguage.googleapis.com/v1beta/'
        'models/gemini-2.5-flash:generateContent'
    )
    assert request.get_header('X-goog-api-key') == 'fixture-gemini-key'
    assert timeout == 12
    body = json.loads(request.data)
    assert body['systemInstruction'] == {
        'parts': [{'text': 'Analyze the supplied text.'}],
    }
    assert body['contents'] == [{
        'role': 'user',
        'parts': [{'text': 'Return the requested JSON.'}],
    }]
    assert body['generationConfig']['temperature'] == 0.2
    assert body['generationConfig']['maxOutputTokens'] == 128
    assert body['generationConfig']['responseMimeType'] == 'application/json'
    provider_schema = body['generationConfig']['responseJsonSchema']
    assert provider_schema['properties']['prediction']['enum'] == [
        'Non-Fallacious',
        'Fallacious',
    ]
    assert 'minLength' not in provider_schema['properties']['content']
    assert 'maxLength' not in provider_schema['properties']['content']
    assert 'fixture-gemini-key' not in request.full_url


def test_gemini_transport_requires_key_before_network(monkeypatch):
    from src.llm.gemini_client import GeminiTransport

    def fail_network(*args, **kwargs):
        raise AssertionError('network should not be called')

    monkeypatch.delenv('MISSING_GEMINI_KEY', raising=False)
    monkeypatch.setattr('src.llm.gemini_client.urlopen', fail_network)
    transport = GeminiTransport(ModelConfig(
        name='gemini-2.5-flash',
        provider='gemini',
        base_url='https://generativelanguage.googleapis.com/v1beta',
        api_key_env='MISSING_GEMINI_KEY',
    ))

    with pytest.raises(RuntimeError, match='MISSING_GEMINI_KEY'):
        transport.complete({})


def test_gemini_client_parses_transport_contract(tmp_path, monkeypatch):
    def urlopen(request, timeout):
        return BytesIO(json.dumps(gemini_envelope()).encode('utf-8'))

    monkeypatch.setenv('TEST_GEMINI_API_KEY', 'fixture-gemini-key')
    monkeypatch.setattr('src.llm.gemini_client.urlopen', urlopen)
    client = Client(
        ModelConfig(
            name='gemini-2.5-flash',
            provider='gemini',
            base_url='https://generativelanguage.googleapis.com/v1beta',
            api_key_env='TEST_GEMINI_API_KEY',
        ),
        tmp_path / 'cache.sqlite',
        tmp_path / 'raw.jsonl',
    )

    result = client.generate(
        system_prompt='Analyze.',
        user_prompt='{"input":"hello"}',
        schema=report_schema('detection'),
        metadata={'role': 'Factual'},
    )

    assert result['prediction'] == 'Fallacious'
    assert client.usage['total_tokens'] == 15
