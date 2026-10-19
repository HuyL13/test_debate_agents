import json
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

from src.io_utils import append_jsonl, digest
from src.llm.cache import Cache
from src.llm.config import ModelConfig
from src.llm.gemini_client import GeminiTransport
from src.llm.mock import MockTransport
from src.llm.openai_client import OpenAITransport
from src.schemas import validate_output


def accumulate_usage(total, usage):
    fields = ('prompt_tokens', 'completion_tokens', 'total_tokens')
    valid = isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in fields)
    details = usage.get('prompt_tokens_details') if isinstance(usage, dict) else None
    cached = details.get('cached_tokens', 0) if isinstance(details, dict) else 0
    valid = valid and type(cached) is int and 0 <= cached <= usage['prompt_tokens']
    if not valid:
        total['missing_usage_responses'] += 1
        return
    for field in fields:
        total[field] += usage[field]
    total['provider_cached_tokens'] += cached


def estimate_cost(config, usage):
    if config.provider == 'mock':
        return 0.0
    if usage['missing_usage_responses']:
        return None
    inp, out = config.input_cost_per_million, config.output_cost_per_million
    if inp is None or out is None:
        return None
    cached = usage['provider_cached_tokens']
    cached_rate = config.cached_input_cost_per_million
    if cached and cached_rate is None:
        return None
    return ((usage['prompt_tokens'] - cached) * inp + cached * (cached_rate or 0)
            + usage['completion_tokens'] * out) / 1_000_000

def _clean_payload(obj):
    if not isinstance(obj, dict):
        return obj
    if 'output' in obj and isinstance(obj['output'], dict):
        return obj['output']
    if 'input' in obj and ('history' in obj or 'instruction' in obj or 'reports' in obj):
        return None
    return obj


def _parse_kv_fallback(text: str) -> dict | None:
    if not isinstance(text, str):
        return None
    import re
    result = {}
    known_keys = [
        'has_fallacy_charge', 'candidate_class', 'defect_mechanism', 'quote',
        'runner_up_class', 'runner_up_defect', 'runner_up_quote',
        'concede_charge', 'alternative_class', 'charitable_interpretation', 'counter_quote',
        'prediction', 'confidence', 'content', 'reasoning'
    ]
    for key in known_keys:
        pattern = r'(?:^|\n)\s*(?:\d+\.\s*)?\**' + key + r'\**\s*[:=]\s*(.+?)(?=\n\s*(?:\d+\.\s*)?\**[a-zA-Z_]+\**\s*[:=]|\Z)'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            val = m.group(1).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1].strip()
            if val.lower() == 'true':
                result[key] = True
            elif val.lower() == 'false':
                result[key] = False
            elif key == 'confidence':
                try:
                    result[key] = float(val)
                except ValueError:
                    result[key] = val
            else:
                result[key] = val
    if any(k in result for k in ('candidate_class', 'prediction', 'concede_charge', 'has_fallacy_charge')):
        return result
    return None


def _extract_json_payload(text: str) -> dict:
    text = text.strip()
    try:
        cleaned = _clean_payload(json.loads(text))
        if cleaned is not None:
            return cleaned
    except json.JSONDecodeError:
        pass
    if r"\'" in text:
        try:
            cleaned = _clean_payload(json.loads(text.replace(r"\'", "'")))
            if cleaned is not None:
                return cleaned
        except json.JSONDecodeError:
            pass
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        try:
            cleaned = _clean_payload(json.loads('\n'.join(lines).strip()))
            if cleaned is not None:
                return cleaned
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end + 1]
        for candidate in (snippet, snippet.replace(r"\'", "'")):
            try:
                cleaned = _clean_payload(json.loads(candidate))
                if cleaned is not None:
                    return cleaned
            except json.JSONDecodeError:
                pass
            if not candidate.endswith('"}'):
                try:
                    cleaned = _clean_payload(json.loads(candidate[:-1] + '"}'))
                    if cleaned is not None:
                        return cleaned
                except json.JSONDecodeError:
                    pass
    kv = _parse_kv_fallback(text)
    if kv is not None:
        return kv
    raise ValueError('No valid JSON object found in response text')


class Client:
    def __init__(self, config, cache_path, audit_path, transport=None):
        self.config = config
        self.cache = Cache(cache_path)
        self.audit_path = audit_path
        if transport is not None:
            self.transport = transport
        elif config.provider == 'mock':
            self.transport = MockTransport()
        elif config.provider == 'gemini':
            self.transport = GeminiTransport(config)
        else:
            self.transport = OpenAITransport(config)
        self.usage = {'api_calls': 0, 'cache_hits': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
                      'total_tokens': 0, 'provider_cached_tokens': 0, 'missing_usage_responses': 0}
        self.model_versions = set()

    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        payload = {'model': self.config.name,
                   'messages': [{'role': 'system', 'content': system_prompt},
                                {'role': 'user', 'content': user_prompt}],
                   'max_completion_tokens': self.config.max_completion_tokens}
        if self.config.temperature is not None:
            payload['temperature'] = self.config.temperature
        if self.config.provider == 'mock' or self.config.structured_output:
            payload['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'cocolofa_output', 'strict': True, 'schema': schema}}
        key = digest({'config': asdict(self.config), 'metadata': metadata, 'payload': payload, 'schema': schema})
        cached = self.cache.get(key)
        if cached is not None:
            validate_output(cached['parsed'], schema)
            if validator:
                validator(cached['parsed'])
            self.usage['cache_hits'] += 1
            self.model_versions.add(cached['model'])
            append_jsonl(self.audit_path, {'timestamp': datetime.now(timezone.utc).isoformat(),
                                         'metadata': metadata, 'cache_key': key, 'cache_hit': True,
                                         'response': cached['response'], 'valid': True})
            return cached['parsed']
        last_error = None
        feedback = None
        for attempt in range(self.config.max_attempts):
            request_payload = deepcopy(payload)
            if feedback:
                request_payload['messages'].append({'role': 'user', 'content':
                    'The previous attempt failed output validation: ' + feedback +
                    '. Generate a fresh complete JSON answer satisfying the schema and all '
                    'execution constraints. Keep the original task and supplied evidence unchanged.'})
            event = {'timestamp': datetime.now(timezone.utc).isoformat(), 'metadata': metadata,
                     'cache_key': key, 'cache_hit': False, 'attempt': attempt + 1,
                     'request': request_payload, 'valid': False}
            started = time.monotonic()
            retryable, parsed, response = True, None, None
            self.usage['api_calls'] += 1
            try:
                response = self.transport.complete(request_payload)
                event['response'] = response
                accumulate_usage(self.usage, response.get('usage'))
                self.model_versions.add(response.get('model', self.config.name))
                choice = response['choices'][0]
                if choice.get('finish_reason') != 'stop' or choice['message'].get('refusal'):
                    raise ValueError('Refused, truncated, or non-final response')
                raw = choice['message'].get('content')
                parsed = None
                if isinstance(raw, str) and raw.strip():
                    try:
                        parsed = _extract_json_payload(raw)
                    except Exception:
                        parsed = None
                if parsed is None:
                    reasoning = choice['message'].get('reasoning_content')
                    if isinstance(reasoning, str) and reasoning.strip():
                        try:
                            parsed = _extract_json_payload(reasoning)
                        except Exception:
                            parsed = None
                if parsed is None:
                    raise ValueError('Missing or invalid JSON response text')
                if isinstance(parsed, dict) and 'output' in parsed and isinstance(parsed['output'], dict):
                    try:
                        validate_output(parsed, schema)
                    except ValueError:
                        parsed = parsed['output']
                try:
                    validate_output(parsed, schema)
                except ValueError as val_err:
                    if isinstance(parsed, dict) and isinstance(schema, dict) and 'properties' in schema:
                        allowed = set(schema['properties'].keys())
                        filtered = {k: v for k, v in parsed.items() if k in allowed}
                        try:
                            validate_output(filtered, schema)
                            parsed = filtered
                            val_err = None
                        except ValueError:
                            pass
                    if val_err is not None:
                        kv = _parse_kv_fallback(raw)
                        if kv is not None:
                            validate_output(kv, schema)
                            parsed = kv
                        else:
                            raise val_err
                if validator:
                    validator(parsed)
                event['valid'] = True
            except HTTPError as exc:
                last_error = exc
                retryable = exc.code in (408, 409, 429) or 500 <= exc.code <= 599
                event['error'] = f'HTTP {exc.code}'
                event['http_error_body'] = exc.read().decode('utf-8', errors='replace')
                event['request_id'] = exc.headers.get('x-request-id') if exc.headers else None
            except (URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
                event['error'] = type(exc).__name__
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                event['error'] = str(exc)
                feedback = str(exc)[:1500]
            except Exception as exc:
                last_error = exc
                retryable = False
                event['error'] = str(exc)
            event['latency_seconds'] = time.monotonic() - started
            append_jsonl(self.audit_path, event)
            if event['valid']:
                self.cache.put(key, {'parsed': parsed, 'response': response,
                                     'model': response.get('model', self.config.name)})
                return parsed
            if not retryable:
                raise last_error
            if attempt + 1 < self.config.max_attempts:
                time.sleep(min(60, self.config.backoff_seconds * 2 ** attempt))
        raise ValueError(f'No valid response after {self.config.max_attempts} attempts: {last_error}') from last_error

    def estimated_cost(self):
        return estimate_cost(self.config, self.usage)
