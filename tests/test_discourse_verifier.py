import json
from types import SimpleNamespace

import pytest

from src.labels import FALLACIES
from src.discourse_classification.pipeline import classify
from src.schemas import validate_output


class VerifierClient:
    def __init__(self, *, extraction_error=False, invalid=None):
        self.stages = []
        self.extraction_error = extraction_error
        self.invalid = invalid

    def generate(self, **kwargs):
        stage = kwargs['metadata']['stage']
        self.stages.append(stage)
        if stage == 'discourse_argument_roles':
            if self.extraction_error:
                raise ValueError('Ungrounded role quote')
            output = {'arguments': []}
        else:
            assert stage == 'discourse_comparative_verification'
            assert kwargs['schema']['properties']['assessments']['type'] == 'object'
            payload = json.loads(kwargs['user_prompt'])
            assert set(payload['definitions']) == set(FALLACIES)
            nodes = [payload['propositions'][0]['id']]
            output = {'label': 'Hasty Generalization', 'reason': 'Limited observation generalized.',
                      'assessments': {label: {'status': 'WEAK' if label == 'Hasty Generalization' else 'ABSENT',
                                       'node_ids': nodes if label == 'Hasty Generalization' else [],
                                       'reason': 'Closest sample-to-population reading.' if label == 'Hasty Generalization' else 'Required mechanism absent.'}
                                      for label in FALLACIES}}
            if self.invalid == 'node':
                output['assessments']['Hasty Generalization']['node_ids'] = ['UNKNOWN']
            elif self.invalid == 'absent':
                output['label'] = 'Appeal to Authority'
            elif self.invalid == 'duplicate':
                output['assessments'].pop('Appeal to Authority')
        validate_output(output, kwargs['schema'])
        kwargs['validator'](output)
        return SimpleNamespace(output=output)


@pytest.mark.parametrize('extraction_error', [False, True])
def test_empty_or_failed_retrieval_still_gets_verified_eight_label_decision(extraction_error):
    client = VerifierClient(extraction_error=extraction_error)
    text = 'One service failed. Every service is unreliable.'
    result = classify(client, {'comment': text}, 'x', method='rules', recovery=False)
    assert result['label'] == 'Hasty Generalization'
    assert result['decision_mode'] == 'verified_weak'
    assert result['calls'] == 2
    assert len(result['verification']) == 8
    assert result['candidates'] == []  # Never fabricate a matched template.
    assert result['evidence'] and all(text[e['start']:e['end']] == e['text'] for e in result['evidence'])
    assert client.stages == ['discourse_argument_roles', 'discourse_comparative_verification']


@pytest.mark.parametrize('invalid', ['node', 'absent', 'duplicate'])
def test_verifier_rejects_unknown_nodes_absent_winner_and_duplicate_labels(invalid):
    with pytest.raises(ValueError):
        classify(VerifierClient(invalid=invalid), {'comment': 'One service failed.'}, 'x', method='rules')
