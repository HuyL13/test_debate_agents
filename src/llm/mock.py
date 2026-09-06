"""Deterministic transport for plumbing smoke tests. NOT an LLM or a benchmark."""
import json

from src.io_utils import digest


class MockTransport:
    def complete(self, payload):
        schema = payload['response_format']['json_schema']['schema']
        properties = schema['properties']
        user = json.loads(payload['messages'][1]['content'])
        seed = int(digest(user.get('input', user))[:8], 16)
        if 'protocol' in properties:
            value = {'protocol': ('round_robin', 'cross_examination')[seed % 2],
                     'topic': 'Offline fixture discussion.', 'reason': 'Synthetic route for smoke testing.',
                     'order': ['Factual', 'Logical', 'Contextual'], 'affirmative': ['Factual'],
                     'negative': ['Logical', 'Contextual'], 'examiner': 'Logical',
                     'max_rounds': min(3, properties['max_rounds']['maximum'])}
        elif 'question' in properties:
            value = {'question': None if 'next targeted' in user.get('instruction', '') else
                     'Which supplied premise supports the conclusion?', 'content': 'Synthetic question/reflection.'}
        else:
            labels = properties['prediction']['enum']
            value = {'prediction': labels[seed % len(labels)], 'confidence': 0.9,
                     'content': 'OFFLINE MOCK: deterministic plumbing fixture, not model analysis.'}
        return {'id': 'mock-' + digest(payload)[:12], 'model': 'offline-mock-v1',
                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value), 'refusal': None}}],
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}}
