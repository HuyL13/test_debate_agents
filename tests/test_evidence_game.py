from copy import deepcopy
import json

import pytest

from src import aligned_classification as aligned
from src import evidence_game as game
from src.data.loader import ModelInput
from src.engine import Engine
from src.labels import FALLACIES
from src.llm.proposal_mock import assessment, inference

TARGET = 'One bad shop proves every shop is bad.'
CANDIDATE = 'Appeal to Authority'
ALTERNATIVE = 'Hasty Generalization'


def prosecutor():
    return {'has_fallacy_charge': True, 'candidate_class': CANDIDATE,
            'defect_mechanism': 'A shop is treated as authority.', 'quote': TARGET,
            'runner_up_class': ALTERNATIVE, 'runner_up_defect': 'One shop to every shop.',
            'runner_up_quote': TARGET, 'inference': inference(TARGET),
            'candidate_assessment': assessment(CANDIDATE, TARGET),
            'runner_up_assessment': assessment(ALTERNATIVE, TARGET), 'ranking_reason': 'Fixture ranking.'}


def review(action='request_comparison', alternative=True):
    return {'action': action, 'inference': inference(TARGET),
            'candidate_assessment': assessment(CANDIDATE, TARGET),
            'alternative_assessment': assessment(ALTERNATIVE, TARGET) if alternative else assessment('None', '', False),
            'candidate_objection': 'The shop is a case, not a cited source.',
            'decisive_difference': '',  # Intentionally unresolved, but worthy of scrutiny.
            'unresolved_commitment': 'Which inference is primary?',
            'comparison': 'Verify the case-to-population claim against the authority reading.'}


def verdict(label=ALTERNATIVE):
    return {'prediction': label, 'confidence': .65, 'content': 'The case is generalized.',
            'selection_reason': 'The text extends one case to all shops.',
            'rejected_reason': 'No source-to-truth step is established.', 'resolution': 'selected',
            'option_assessments': [assessment(CANDIDATE, TARGET), assessment(ALTERNATIVE, TARGET)],
            'probabilities': {c: .65 if c == label else .05 for c in FALLACIES}}


class Scripted:
    def __init__(self, values):
        self.values = deepcopy(values); self.calls = []

    def generate(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        value = self.values.pop(0)
        kwargs['validator'](value)
        return value


def run(r, v=None):
    client = Scripted([prosecutor(), r, v or verdict()])
    result = Engine(client, task='classification', adaptive_policy='adversarial',
                    defender_policy='proposal_2').run(ModelInput('', '', TARGET), {'sample_id': 'fixture'})
    return result, client


def test_grounded_question_without_decisive_difference_reaches_verifier():
    r = review()
    r['alternative_assessment']['condition_status'] = 'uncertain'
    result, client = run(r)
    assert len(client.calls) == 3
    assert result['prediction'] == ALTERNATIVE
    assert result['defender_validation']['effective_decision'] == 'request_comparison'
    assert result['defender_review']['decisive_difference'] == ''
    assert result['arbiter']['game_trace']['alternative_from_review'] is True
    assert result['arbiter']['game_trace']['rebuttal_rounds'] == 0


@pytest.mark.parametrize('action', game.ACTIONS)
def test_no_defender_action_can_force_candidate_to_survive(action):
    result, client = run(review(action, alternative=action == 'request_comparison'))
    assert result['prediction'] == ALTERNATIVE
    assert len(client.calls) == 3
    options = json.loads(client.calls[-1]['user_prompt'])['reports']['options']
    assert [o['class'] for o in options] == sorted([CANDIDATE, ALTERNATIVE])
    assert 'prosecutor' not in json.dumps(options).lower()


def test_criticism_does_not_force_an_alternative_win():
    result, _ = run(review(), verdict(CANDIDATE))
    assert result['prediction'] == CANDIDATE
    assert result['arbiter']['selection_policy'] == 'verified_comparison'
    assert result['arbiter']['game_trace']['decision_overrode_initial'] is False


def test_uncertainty_and_outside_candidate_probability_are_preserved():
    v = verdict()
    v['resolution'] = 'both_unsupported'
    for a in v['option_assessments']:
        a.update(condition_status='not_established', missing_condition='Unresolved fixture condition.')
    v['probabilities'] = {c: 0 for c in FALLACIES}
    v['probabilities'].update({ALTERNATIVE: .3, CANDIDATE: .2, 'Appeal to Nature': .5})
    v['confidence'] = .3
    result, _ = run(review('insufficient_evidence'), v)
    assert result['prediction'] == ALTERNATIVE
    assert result['arbiter']['uncertainty'] is True
    assert result['arbiter']['game_trace']['outside_candidate_mass'] == .5


@pytest.mark.parametrize('mutate, message', [
    (lambda r: r.update(candidate_objection=''), 'concrete candidate objection'),
    (lambda r: r.update(alternative_assessment=assessment('None', '', False)), 'grounded'),
    (lambda r: r['alternative_assessment'].update(evidence_quote='not in target'), 'TARGET substring'),
])
def test_review_contract_rejects_empty_or_fabricated_attacks(mutate, message):
    r = review(); mutate(r)
    with pytest.raises(ValueError, match=message):
        game.validate_defender(r, TARGET, CANDIDATE)


def test_insufficient_and_uphold_have_distinct_contracts():
    r = review('insufficient_evidence'); r['unresolved_commitment'] = ''
    with pytest.raises(ValueError, match='unresolved textual'):
        game.validate_defender(r, TARGET, CANDIDATE)
    r = review('uphold'); r['candidate_assessment']['condition_status'] = 'uncertain'
    with pytest.raises(ValueError, match='supported candidate'):
        game.validate_defender(r, TARGET, CANDIDATE)


@pytest.mark.parametrize('mutate, message', [
    (lambda v: v['probabilities'].update({CANDIDATE: .3}), 'sum to one'),
    (lambda v: v.update(confidence=.9), 'Confidence must equal'),
    (lambda v: v['probabilities'].update({CANDIDATE: .7, ALTERNATIVE: 0}), 'maximize'),
])
def test_probability_contract_is_global_and_internally_consistent(mutate, message):
    v = verdict(); mutate(v)
    with pytest.raises(ValueError, match=message):
        game.validate_arbiter(v, TARGET, [CANDIDATE, ALTERNATIVE])


def test_prosecutor_contract_and_prompt_are_identical_between_proposals():
    _, client = run(review())
    call = client.calls[0]
    assert call['system_prompt'] == aligned.system_prompt('Prosecutor', aligned.prosecutor_schema())
    assert call['schema'] == aligned.prosecutor_schema()
    for call in client.calls:
        assert 'gold' not in json.loads(call['user_prompt'])
        assert json.dumps(call['schema']) in call['system_prompt']


@pytest.mark.parametrize('kwargs', [
    {'task': 'detection', 'adaptive_policy': 'adversarial'},
    {'task': 'classification', 'adaptive_policy': 'planner'},
    {'task': 'classification', 'adaptive_policy': 'adversarial', 'mode': 'single'},
])
def test_game_profile_is_explicit_and_classification_only(kwargs):
    with pytest.raises(ValueError, match='defender_policy'):
        Engine(None, defender_policy='proposal_2', **kwargs)


def test_mock_replays_share_exact_prosecutor_and_pairwise_report(tmp_path):
    from pathlib import Path
    from src.defender_experiment import build_snapshot, run_experiment
    from src.game_evaluation import compare_replays
    from src.io_utils import file_hash, write_json
    from src.runner import load_config
    data = tmp_path/'data'; data.mkdir()
    write_json(data/'dev.json', [{'sample_id': 'fixture', 'title': '', 'parent_comment': '',
                                'comment': TARGET, 'gold': ALTERNATIVE}])
    saved = build_snapshot([('fixture', ModelInput('', '', TARGET), prosecutor())],
                           dataset_hash=file_hash(data/'dev.json'), split='dev', context='paper')
    snap = tmp_path/'snapshot.json'; write_json(snap, saved)
    configs = []
    for profile in ('proposal-1', 'proposal-2'):
        cfg = load_config(f'configs/classification.adversarial.{profile}.marketplace.yaml')
        cfg['data_dir'] = str(data); cfg['cache_dir'] = str(tmp_path/'cache')
        cfg['model'].update(provider='mock', name='offline-mock-v1')
        directory = tmp_path/profile
        result = run_experiment(cfg, snap, directory)
        assert result['status'] == 'complete'
        assert run_experiment(cfg, snap, directory, resume=True)['status'] == 'complete'
        configs.append((cfg, directory))
    report = compare_replays(configs[0][1], configs[1][1])
    assert report['paired_count'] == 1 and report['synthetic'] is True
    assert report['candidate']['forecast_count'] == 1
    calls = [json.loads(line) for line in (configs[1][1]/'raw_calls.jsonl').read_text().splitlines()]
    assert {c['metadata']['role'] for c in calls} == {'Defender', 'DialecticalArbiter'}
    assert report['candidate']['actions'] == {'uphold': 1}
    rows_path = configs[1][1]/'predictions.jsonl'
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    rows[0]['prosecutor']['quote'] = 'changed'
    rows_path.write_text(json.dumps(rows[0])+'\n')
    with pytest.raises(ValueError, match='exact Prosecutor'):
        compare_replays(configs[0][1], configs[1][1])
