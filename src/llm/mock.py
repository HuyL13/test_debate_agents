"""Deterministic transport for plumbing smoke tests. NOT an LLM or a benchmark."""
import json

from src.io_utils import digest


class MockTransport:
    def complete(self, payload):
        schema = payload['response_format']['json_schema']['schema']
        properties = schema['properties']
        user = json.loads(payload['messages'][1]['content'])
        seed = int(digest(user.get('input', user))[:8], 16)
        comment = user.get('input', {}).get('comment', '')
        quote = comment[:220]
        if 'protocol' in properties:
            value = {'protocol': ('round_robin', 'cross_examination')[seed % 2],
                     'topic': 'Offline fixture discussion.', 'reason': 'Synthetic route for smoke testing.',
                     'order': ['Factual', 'Logical', 'Contextual'], 'affirmative': ['Factual'],
                     'negative': ['Logical', 'Contextual'], 'examiner': 'Logical',
                     'max_rounds': min(3, properties['max_rounds']['maximum'])}
            for field in ('order', 'affirmative', 'negative'):
                if 'enum' in properties[field]:
                    value[field] = properties[field]['enum'][0]
        elif 'question' in properties:
            value = {'question': None if 'next targeted' in user.get('instruction', '') else
                     'Which supplied premise supports the conclusion?', 'content': 'Synthetic question/reflection.'}
        elif 'validated_dimensions' in properties:
            dimensions = {
                'acceptability': 'not_applicable',
                'relevance': 'supported',
                'sufficiency': 'supported',
            }
            if 'None' in properties['candidate_type']['enum']:
                value = {
                    'validated_dimensions': dimensions,
                    'candidate_type': 'None',
                    'nearest_competitor': 'None',
                    'mapping_reason': 'The offline fixture establishes no closed-set candidate.',
                    'prediction': 'Non-Fallacious',
                    'content': 'OFFLINE MOCK ARS arbiter fixture.',
                }
            else:
                candidate = properties['candidate_type']['enum'][seed % len(properties['candidate_type']['enum'])]
                competitors = [label for label in properties['nearest_competitor']['enum'] if label != candidate]
                value = {
                    'validated_dimensions': dimensions,
                    'candidate_type': candidate,
                    'nearest_competitor': competitors[0] if competitors else candidate,
                    'mapping_reason': 'The offline fixture maps the validated dimensions to one closed-set candidate.',
                    'prediction': candidate,
                    'content': 'OFFLINE MOCK ARS arbiter fixture.',
                }
        elif 'decomposition_check' in properties:
            diagnosis = {
                'decomposition_check': {'status': 'accept', 'corrections': []},
                'premise_ids': [],
                'dimension_status': 'not_applicable',
                'finding': 'The offline fixture records the assigned ARS dimension.',
                'supporting_quote': quote,
                'charitable_reading': 'No stronger conclusion is drawn from the fixture.',
            }
            if 'acceptability_basis' in properties:
                diagnosis.update(acceptability_basis='none', problematic_commitment='')
            elif 'relevance_gap' in properties:
                diagnosis.update(conclusion_id=None, relevance_gap='')
            else:
                diagnosis.update(conclusion_id=None, missing_warrant='', scope_or_strength_gap='')
            if 'review_action' in properties:
                diagnosis = {
                    'review_action': 'keep',
                    'peer_effect': 'The offline fixture leaves the initial dimension unchanged.',
                    **diagnosis,
                }
            value = diagnosis
        elif 'main_conclusion_id' in properties:
            if comment:
                claims = [{'id': 'C1', 'source': 'target_comment', 'role': 'conclusion',
                           'text': comment[:300], 'qualifiers': [], 'modality': 'asserted'}]
                main_conclusion_id = 'C1'
            else:
                claims = []
                main_conclusion_id = None
            value = {'argumentative_status': 'assertion', 'claims': claims,
                     'main_conclusion_id': main_conclusion_id,
                     'implicit_assumptions': [], 'inference_links': [],
                     'scope_notes': [], 'uncertainty': []}
        elif 'premises' in properties:
            value = {'premises': [], 'conclusion': user['input']['comment']}
        elif 'argumentative_status' in properties:
            value = {'argumentative_status': 'explicit_argument',
                     'claims': [{'id': 'C1', 'source': 'target_comment', 'role': 'conclusion',
                                 'text': user['input']['comment']}],
                     'conclusion_id': 'C1', 'implicit_assumptions': [],
                     'reasoning_relation': 'OFFLINE MOCK decomposition.',
                     'scope_notes': [], 'uncertainty': []}
        elif 'issue_status' in properties:
            value = {'issue_status': 'present', 'diagnosis': 'OFFLINE MOCK diagnostic fixture.',
                     'supporting_quote': user['input']['comment'],
                     'structure_objection': 'OFFLINE MOCK structure note.',
                     'alternative_interpretation': 'OFFLINE MOCK alternative.'}
        elif 'candidate_type' in properties:
            value = {'candidate_type': 'None', 'status': 'rejected',
                     'necessary_conditions_met': False, 'sufficient_evidence': False,
                     'supporting_quote': user['input']['comment'],
                     'premise': '', 'conclusion': '', 'defective_inference': '',
                     'strongest_nonfallacious_reading': 'OFFLINE MOCK non-fallacious reading.',
                     'auxiliary_observation': 'OFFLINE MOCK candidate fixture.'}
        elif 'decision' in properties:
            value = {'decision': 'keep', 'diagnosis': 'OFFLINE MOCK review fixture.',
                     'supporting_quote': user['input']['comment'],
                     'response_to_other_diagnoses': 'OFFLINE MOCK response.',
                     'remaining_uncertainty': 'OFFLINE MOCK uncertainty.'}
        else:
            labels = properties['prediction']['enum']
            value = {'prediction': labels[seed % len(labels)],
                     'content': 'OFFLINE MOCK: deterministic plumbing fixture, not model analysis.'}
            if 'confidence' in properties:
                value['confidence'] = 0.9
            if 'supporting_quote' in properties:
                value['supporting_quote'] = user['input']['comment']
        return {'id': 'mock-' + digest(payload)[:12], 'model': 'offline-mock-v1',
                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value), 'refusal': None}}],
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}}
