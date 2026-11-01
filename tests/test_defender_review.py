from copy import deepcopy

import pytest

from src.defender_review import normalize_defender_review, validate_defender_review


TARGET = 'One bad shop proves every shop is bad.'
PROSECUTOR = {'candidate_class': 'Appeal to Majority', 'quote': TARGET}


def review(decision='challenge'):
    return {
        'decision': decision, 'premise_quote': 'One bad shop',
        'conclusion_quote': 'every shop is bad',
        'inference_summary': 'A single case is extended to all shops.',
        'candidate_assessment': {'status': 'not_established',
            'condition': 'Popularity must justify the conclusion.',
            'evidence_quote': TARGET, 'explanation': 'The argument uses a case rather than consensus.'},
        'alternative_assessment': {'class': 'Hasty Generalization', 'status': 'supported',
            'premise_quote': 'One bad shop', 'conclusion_quote': 'every shop is bad',
            'explanation': 'One shop is used as a sample for all shops.'},
        'decisive_difference': 'Case-to-population rather than consensus-to-truth.',
        'counter_quote': TARGET, 'charitable_interpretation': 'Candidate lacks consensus; HG explains the inference.',
    }


def test_grounded_challenge_accepts_shared_quote_and_keeps_raw():
    value = review(); original = deepcopy(value)
    result = normalize_defender_review(PROSECUTOR, value, TARGET)
    assert not result['concede_charge']
    assert result['alternative_class'] == 'Hasty Generalization'
    assert result['raw_report'] == original == value
    assert result['validation']['effective_decision'] == 'challenge'


@pytest.mark.parametrize('change,reason', [
    ('supported_candidate', 'candidate_not_rebutted'),
    ('unsupported_alternative', 'alternative_not_supported'),
    ('no_difference', 'missing_decisive_difference'),
    ('same_class', 'same_class'),
    ('no_alternative_quote', 'missing_alternative_evidence'),
])
def test_insufficient_challenge_defers_without_claiming_agreement(change, reason):
    value = review()
    if change == 'supported_candidate': value['candidate_assessment']['status'] = 'supported'
    if change == 'unsupported_alternative': value['alternative_assessment']['status'] = 'uncertain'
    if change == 'no_difference': value['decisive_difference'] = ''
    if change == 'same_class': value['alternative_assessment']['class'] = 'Appeal to Majority'
    if change == 'no_alternative_quote': value['alternative_assessment']['premise_quote'] = ''; value['alternative_assessment']['conclusion_quote'] = ''
    result = normalize_defender_review(PROSECUTOR, value, TARGET)
    assert result['concede_charge'] is True  # legacy adapter only
    assert result['validation']['submitted_decision'] == 'challenge'
    assert result['validation']['effective_decision'] == 'defer'
    assert reason in result['validation']['gate_reasons']
    assert result['raw_report'] == value


@pytest.mark.parametrize('decision', ['uphold', 'defer'])
def test_non_challenge_keeps_distinct_decision_in_audit(decision):
    result = normalize_defender_review(PROSECUTOR, review(decision), TARGET)
    assert result['concede_charge'] is True
    assert result['alternative_class'] == 'None'
    assert result['validation']['effective_decision'] == decision


def test_missing_condition_can_use_empty_quote_without_fabrication():
    value = review(); value['candidate_assessment']['evidence_quote'] = ''
    value['premise_quote'] = ''  # implicit premise, described in inference_summary
    validate_defender_review(value, TARGET)
    assert normalize_defender_review(PROSECUTOR, value, TARGET)['validation']['effective_decision'] == 'challenge'


@pytest.mark.parametrize('field', ['counter_quote', 'premise_quote'])
def test_hallucinated_quote_rejected(field):
    value = review(); value[field] = 'not in target'
    with pytest.raises(ValueError, match='target'):
        validate_defender_review(value, TARGET)


def test_missing_counter_quote_is_invalid_even_when_upholding():
    value = review('uphold'); del value['counter_quote']
    with pytest.raises(ValueError, match='counter_quote'):
        validate_defender_review(value, TARGET)


def test_v2_profile_reuses_original_arbiter_contract():
    import json
    from src.engine import Engine
    from src.data.loader import ModelInput
    from src.adversarial_prompts import adversarial_system_prompt
    prosecutor = {'has_fallacy_charge': True, **PROSECUTOR, 'defect_mechanism': 'Consensus.',
                  'runner_up_class': 'Hasty Generalization', 'runner_up_quote': TARGET,
                  'runner_up_defect': 'A case is generalized.'}
    requests = []
    class Scripted:
        def generate(self, **kw):
            requests.append(kw)
            role = kw['metadata']['role']
            if role == 'Prosecutor': value = deepcopy(prosecutor)
            elif role == 'Defender': value = review()
            else: value = {'prediction': 'Hasty Generalization', 'confidence': .8, 'content': 'Sample leap.'}
            if kw.get('validator'): kw['validator'](value)
            return value
    result = Engine(Scripted(), task='classification', adaptive_policy='adversarial',
                    defender_policy='evidence_v2').run(ModelInput('', '', TARGET), {'sample_id': 'fixture'})
    assert result['prediction'] == 'Hasty Generalization'
    assert result['defender_validation']['effective_decision'] == 'challenge'
    assert result['defender_review'] == review()
    assert len(requests) == 4
    assert requests[0]['system_prompt'] == adversarial_system_prompt('Prosecutor', 'classification', use_patterns=False)
    for request in requests[2:]:
        assert request['system_prompt'] == adversarial_system_prompt('DialecticalArbiter', 'classification')
        reports = json.loads(request['user_prompt'])['reports']
        assert set(reports) == {'comment', 'option_1', 'option_2'}
        assert all(set(reports[k]) == {'class', 'quote'} for k in ['option_1', 'option_2'])


@pytest.mark.parametrize('options', [
    {'task': 'detection', 'adaptive_policy': 'adversarial'},
    {'task': 'classification', 'adaptive_policy': 'planner'},
    {'task': 'classification', 'adaptive_policy': 'adversarial', 'mode': 'single'},
])
def test_v2_rejects_unsupported_engine_combinations(options):
    from src.engine import Engine
    with pytest.raises(ValueError, match='defender_policy'):
        Engine(None, defender_policy='evidence_v2', **options)
