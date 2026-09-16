"""Native REST transport for Google's Gemini generateContent API."""

import json
import os
from urllib.request import Request, urlopen


_GEMINI_SCHEMA_KEYS = {
    '$id',
    '$defs',
    '$ref',
    '$anchor',
    'type',
    'format',
    'title',
    'description',
    'enum',
    'items',
    'prefixItems',
    'minItems',
    'maxItems',
    'minimum',
    'maximum',
    'anyOf',
    'oneOf',
    'properties',
    'additionalProperties',
    'required',
}


def _gemini_schema(schema):
    """Keep the JSON Schema subset accepted by Gemini structured output."""
    if not isinstance(schema, dict):
        raise ValueError('Gemini response schema must be an object')

    result = {}
    schema_type = schema.get('type')
    if isinstance(schema_type, list):
        result['anyOf'] = [
            {'type': item}
            for item in schema_type
        ]
    elif schema_type is not None:
        result['type'] = schema_type

    for key, value in schema.items():
        if key not in _GEMINI_SCHEMA_KEYS or key == 'type':
            continue
        if key == 'properties':
            if not isinstance(value, dict):
                raise ValueError('Gemini schema properties must be an object')
            result[key] = {
                name: _gemini_schema(subschema)
                for name, subschema in value.items()
            }
        elif key in ('items',):
            result[key] = _gemini_schema(value)
        elif key in ('anyOf', 'oneOf', 'prefixItems'):
            if not isinstance(value, list):
                raise ValueError(f'Gemini schema {key} must be an array')
            result[key] = [_gemini_schema(item) for item in value]
        elif key == 'additionalProperties' and isinstance(value, dict):
            result[key] = _gemini_schema(value)
        else:
            result[key] = value

    return result


def _text_part(content):
    if not isinstance(content, str):
        raise ValueError('Gemini transport supports text message content only')
    return {'text': content}


def _gemini_contents(messages):
    if not isinstance(messages, list):
        raise ValueError('Gemini request messages must be an array')

    system_parts = []
    contents = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError('Gemini request messages must be objects')
        role = message.get('role')
        content = _text_part(message.get('content'))
        if role == 'system':
            system_parts.append(content)
            continue
        if role not in ('user', 'assistant'):
            raise ValueError(f'Unsupported Gemini message role: {role}')

        gemini_role = 'model' if role == 'assistant' else 'user'
        if contents and contents[-1]['role'] == gemini_role:
            contents[-1]['parts'].append(content)
        else:
            contents.append({'role': gemini_role, 'parts': [content]})

    if not contents:
        raise ValueError('Gemini request requires at least one user or assistant message')
    return system_parts, contents


def _request_body(payload):
    system_parts, contents = _gemini_contents(payload.get('messages'))
    body = {'contents': contents}
    if system_parts:
        body['systemInstruction'] = {'parts': system_parts}

    generation = {}
    if payload.get('temperature') is not None:
        generation['temperature'] = payload['temperature']
    if payload.get('max_completion_tokens') is not None:
        generation['maxOutputTokens'] = payload['max_completion_tokens']

    response_format = payload.get('response_format')
    if response_format:
        format_type = response_format.get('type')
        if format_type == 'json_schema':
            schema_wrapper = response_format.get('json_schema', {})
            schema = schema_wrapper.get('schema')
            generation['responseMimeType'] = 'application/json'
            generation['responseJsonSchema'] = _gemini_schema(schema)
        elif format_type == 'json_object':
            generation['responseMimeType'] = 'application/json'
        else:
            raise ValueError(f'Unsupported Gemini response format: {format_type}')

    if generation:
        body['generationConfig'] = generation
    return body


def _finish_reason(value):
    reason = str(value or '').upper()
    if reason == 'STOP':
        return 'stop'
    if reason == 'MAX_TOKENS':
        return 'length'
    return reason.casefold() or 'unknown'


def _response_text(candidate):
    content = candidate.get('content') or {}
    parts = content.get('parts') if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return ''
    return ''.join(
        part.get('text', '')
        for part in parts
        if isinstance(part, dict) and isinstance(part.get('text'), str)
    )


def _usage(raw):
    metadata = raw.get('usageMetadata')
    if not isinstance(metadata, dict):
        return {}
    return {
        'prompt_tokens': metadata.get('promptTokenCount'),
        'completion_tokens': metadata.get('candidatesTokenCount'),
        'total_tokens': metadata.get('totalTokenCount'),
    }


class GeminiTransport:
    """Translate the internal chat contract to Gemini's native REST contract."""

    def __init__(self, config):
        self.config = config

    def complete(self, payload):
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise RuntimeError(
                f'Set {self.config.api_key_env} in the environment before an API run'
            )

        model = self.config.name.removeprefix('models/')
        endpoint = (
            self.config.base_url.rstrip('/')
            + '/models/'
            + model
            + ':generateContent'
        )
        request = Request(
            endpoint,
            data=json.dumps(
                _request_body(payload),
                allow_nan=False,
            ).encode('utf-8'),
            headers={
                'x-goog-api-key': key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            body = response.read().decode('utf-8')
        try:
            raw = json.loads(body)
        except json.JSONDecodeError:
            return {'unparsed_body': body}
        if not isinstance(raw, dict):
            return {'unparsed_body': body}

        candidates = raw.get('candidates')
        if not isinstance(candidates, list) or not candidates:
            return {**raw, 'provider_response': raw}

        candidate = candidates[0]
        return {
            'id': raw.get('responseId', ''),
            'model': raw.get('modelVersion', self.config.name),
            'provider': 'gemini',
            'provider_response': raw,
            'choices': [{
                'finish_reason': _finish_reason(candidate.get('finishReason')),
                'message': {
                    'content': _response_text(candidate),
                    'refusal': None,
                },
            }],
            'usage': _usage(raw),
        }
