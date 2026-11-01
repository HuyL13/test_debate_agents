"""Behavioral contracts and routing; fixtures do not measure prompt accuracy."""
from copy import deepcopy
import json

import pytest

from src import aligned_classification as aligned
from src.data.loader import ModelInput
from src.engine import Engine
from src.llm.proposal_mock import assessment, inference, response

TARGET = 'One bad shop proves every shop is bad.'
CANDIDATE = 'Appeal to Majority'
ALTERNATIVE = 'Hasty Generalization'


def prosecutor():
    return {'has_fallacy_charge': True, 'candidate_class': CANDIDATE,
            'defect_mechanism': 'Popular agreement offered as proof.', 'quote': TARGET,
            'runner_up_class': ALTERNATIVE, 'runner_up_defect': 'One case to all shops.',
            'runner_up_quote': TARGET, 'inference': inference(TARGET),
            'candidate_assessment': assessment(CANDIDATE, TARGET),
            'runner_up_assessment': assessment(ALTERNATIVE, TARGET),
            'ranking_reason': 'Fixture deliberately offers a mistaken primary diagnosis.'}


def review(decision='challenge'):
    return {'decision': decision, 'inference': inference(TARGET),
            'candidate_assessment': assessment(CANDIDATE, TARGET, False),
            'alternative_assessment': assessment(ALTERNATIVE, TARGET),
            'candidate_objection': 'No consensus is offered as proof.',
            'decisive_difference': 'Case-to-population, not agreement-to-truth.',
            'unresolved_commitment': 'Unclear primary inference.' if decision == 'defer' else '',
            'comparison': 'The limited case is generalized to all shops.'}


def verdict(label=ALTERNATIVE, resolution='selected'):
    return {'prediction': label, 'confidence': .7, 'content': 'The sample is extended to a group.',
            'selection_reason': 'Case-to-population leap.', 'rejected_reason': 'No consensus premise.',
            'resolution': resolution, 'option_assessments': [assessment(CANDIDATE, TARGET, False),
                                                          assessment(ALTERNATIVE, TARGET)]}


class Scripted:
    def __init__(self, values):
        self.values = deepcopy(values)
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        value = self.values.pop(0)
        kwargs['validator'](value)
        return value


def run(values):
    client = Scripted(values)
    result = Engine(client, task='classification', adaptive_policy='adversarial',
                    defender_policy='proposal_1').run(ModelInput('', '', TARGET), {'sample_id': 'fixture'})
    return result, client


def test_contested_pipeline_passes_full_dossiers_and_swaps_without_gold():
    result, client = run([prosecutor(), review(), verdict(), verdict()])
    assert result['prediction'] == ALTERNATIVE
    assert result['defender_validation']['effective_decision'] == 'challenge'
    assert len(client.calls) == 4
    options_a = json.loads(client.calls[2]['user_prompt'])['reports']['options']
    options_b = json.loads(client.calls[3]['user_prompt'])['reports']['options']
    assert options_b == list(reversed(options_a))
    assert options_a[0]['objection'] == review()['candidate_objection']
    assert options_a[1]['assessment'] == review()['alternative_assessment']
    for call in client.calls:
        payload = json.loads(call['user_prompt'])
        assert 'gold' not in payload and 'gold' not in payload['input']
        assert json.dumps(aligned.DEFINITIONS) in call['system_prompt']
        assert json.dumps(call['schema']) in call['system_prompt']


def test_proposal_one_retains_conservative_disagreement_policy():
    candidate_win = verdict(CANDIDATE)
    candidate_win['option_assessments'][0] = assessment(CANDIDATE, TARGET)
    result, _ = run([prosecutor(), review(), verdict(), candidate_win])
    assert result['prediction'] == CANDIDATE
    assert result['arbiter']['selection_policy'] == 'unanimous_alternative'


def test_defer_preserves_audit_and_does_not_claim_model_upheld():
    v = verdict(CANDIDATE)
    v['option_assessments'] = [assessment(CANDIDATE, TARGET)]
    result, client = run([prosecutor(), review('defer'), v])
    assert result['prediction'] == CANDIDATE
    assert result['defender_validation']['effective_decision'] == 'defer'
    assert result['defender_review']['alternative_assessment']['class'] == ALTERNATIVE
    assert len(client.calls) == 3


def test_unsupported_consensus_is_recorded_as_fallback_not_semantic_success():
    v = verdict(ALTERNATIVE, 'both_unsupported')
    v['option_assessments'][1] = assessment(ALTERNATIVE, TARGET, False)
    result, _ = run([prosecutor(), review(), v, v])
    assert result['prediction'] == CANDIDATE
    assert result['arbiter']['uncertainty'] is True
    assert result['arbiter']['confidence'] == 0


@pytest.mark.parametrize('mutate, message', [
    (lambda r: r['alternative_assessment'].update(evidence_quote='invented text'), 'TARGET substring'),
    (lambda r: r['candidate_assessment'].update(missing_condition=''), 'missing condition'),
    (lambda r: r['candidate_assessment'].update(**{'class': ALTERNATIVE}), 'committed candidate'),
    (lambda r: r['alternative_assessment'].update(**{'class': CANDIDATE}), 'must differ'),
    (lambda r: r.update(comparison=' '), 'nonblank'),
    (lambda r: r['inference'].update(premise_quote='', implicit_warrant='Imagined premise', warrant_basis='none'), 'basis'),
])
def test_invalid_evidence_and_inconsistent_commitments_fail(mutate, message):
    r = review(); mutate(r)
    with pytest.raises(ValueError, match=message):
        aligned.validate_defender(r, TARGET, CANDIDATE)


def test_supported_secondary_mechanism_is_distinct_from_uncertainty():
    r = review()
    r['candidate_assessment'] = assessment(CANDIDATE, TARGET)
    r['candidate_assessment']['inference_role'] = 'secondary'
    aligned.validate_defender(r, TARGET, CANDIDATE)
    assert aligned.normalize_review(prosecutor(), r)['validation']['effective_decision'] == 'challenge'
    before = deepcopy(r)
    r['decisive_difference'] = ''
    normalized = aligned.normalize_review(prosecutor(), r)
    assert normalized['validation']['effective_decision'] == 'defer'
    assert 'missing_decisive_difference' in normalized['validation']['gate_reasons']
    assert before['candidate_assessment'] == r['candidate_assessment']


def test_runner_up_can_admit_missing_evidence_and_exact_quotes_are_required():
    p = prosecutor()
    p['runner_up_assessment'] = assessment(ALTERNATIVE, TARGET, False)
    p['runner_up_quote'] = ''
    aligned.validate_prosecutor(p, TARGET)
    p['quote'] = 'One bad shop...every shop is bad'
    with pytest.raises(ValueError, match='TARGET substring'):
        aligned.validate_prosecutor(p, TARGET)


def test_arbiter_must_verify_every_option_and_support_selected_winner():
    v = verdict()
    v['option_assessments'][0] = deepcopy(v['option_assessments'][1])
    with pytest.raises(ValueError, match='exactly once'):
        aligned.validate_arbiter(v, TARGET, [CANDIDATE, ALTERNATIVE])
    v = verdict(CANDIDATE)
    with pytest.raises(ValueError, match='supported winner'):
        aligned.validate_arbiter(v, TARGET, [CANDIDATE, ALTERNATIVE])


@pytest.mark.parametrize('kwargs', [
    {'task': 'detection', 'adaptive_policy': 'adversarial'},
    {'task': 'classification', 'adaptive_policy': 'planner'},
    {'task': 'classification', 'adaptive_policy': 'adversarial', 'mode': 'single'},
])
def test_profile_rejects_unsupported_engine_combinations(kwargs):
    with pytest.raises(ValueError, match='defender_policy'):
        Engine(None, defender_policy='proposal_1', **kwargs)


def test_profile_config_changes_experiment_identity():
    from src.runner import validate_config
    import yaml
    from pathlib import Path
    config = validate_config(yaml.safe_load(Path('configs/classification.adversarial.proposal-1.marketplace.yaml').read_text()))
    assert config['engine']['defender_policy'] == 'proposal_1'
    assert 'proposal-1' in config['output_dir']


def test_aligned_snapshot_replays_unchanged_and_rejects_legacy_contract(tmp_path):
    from src.defender_experiment import build_snapshot, validate_snapshot, ReplayClient
    from src.io_utils import digest
    model_input = ModelInput('', '', TARGET)
    saved = build_snapshot([('fixture', model_input, prosecutor())], dataset_hash='hash', split='dev', context='paper')
    validate_snapshot(saved, {'fixture': model_input}, dataset_hash='hash', split='dev', context='paper')
    replay = ReplayClient(None, saved)
    value = replay.generate(metadata={'role': 'Prosecutor', 'stage': 'indictment', 'sample_id': 'fixture'},
                            user_prompt=json.dumps({'input': model_input.as_dict()}),
                            validator=lambda v: aligned.validate_prosecutor(v, TARGET))
    assert value == prosecutor()
    assert saved['records'][0]['input_hash'] == digest(model_input.as_dict())


def test_profile_replay_completes_and_old_snapshot_fails_before_client(tmp_path):
    from src.defender_experiment import build_snapshot, prepare, run_experiment
    from src.io_utils import file_hash, write_json
    from src.runner import load_config
    config = load_config('configs/classification.adversarial.proposal-1.marketplace.yaml')
    config['model'].update(provider='mock', name='offline-mock-v1')
    config['data_dir'] = str(tmp_path / 'data')
    config['cache_dir'] = str(tmp_path / 'cache')
    from pathlib import Path
    Path(config['data_dir']).mkdir()
    path = Path(config['data_dir'], 'dev.json')
    write_json(path, [{'sample_id': 'fixture', 'title': '', 'parent_comment': '',
                       'comment': TARGET, 'gold': ALTERNATIVE}])
    saved = build_snapshot([('fixture', ModelInput('', '', TARGET), prosecutor())],
                           dataset_hash=file_hash(path), split='dev', context='paper')
    snap = tmp_path / 'snapshot.json'; write_json(snap, saved)
    result = run_experiment(config, snap, tmp_path / 'out')
    assert result['status'] == 'complete'
    calls = [json.loads(line) for line in (tmp_path / 'out/raw_calls.jsonl').read_text().splitlines()]
    assert {r['metadata']['role'] for r in calls} == {'Defender', 'DialecticalArbiter'}
    assert run_experiment(config, snap, tmp_path / 'out', resume=True)['status'] == 'complete'
    legacy = {k: v for k, v in prosecutor().items() if k in (
        'has_fallacy_charge', 'candidate_class', 'quote', 'defect_mechanism',
        'runner_up_class', 'runner_up_quote', 'runner_up_defect')}
    write_json(snap, build_snapshot([('fixture', ModelInput('', '', TARGET), legacy)],
                                   dataset_hash=file_hash(path), split='dev', context='paper'))
    with pytest.raises(ValueError, match='contract does not match'):
        prepare(config, snap)


def test_mock_cli_completes_and_resume_is_idempotent(tmp_path):
    from src.runner import load_config, execute
    config = load_config('configs/classification.adversarial.proposal-1.marketplace.yaml')
    config['model'].update(provider='mock', name='offline-mock-v1')
    config['data_dir'] = str(tmp_path / 'data')
    from pathlib import Path
    Path(config['data_dir']).mkdir()
    Path(config['data_dir'], 'dev.json').write_text(json.dumps([
        {'sample_id': 'fixture', 'title': '', 'parent_comment': '', 'comment': TARGET, 'gold': ALTERNATIVE}]))
    config['output_dir'] = str(tmp_path / 'out'); config['cache_dir'] = str(tmp_path / 'cache')
    assert execute(config)['status'] == 'complete'
    first = Path(config['output_dir'], 'predictions.jsonl').read_bytes()
    assert execute(config, resume=True)['status'] == 'complete'
    assert Path(config['output_dir'], 'predictions.jsonl').read_bytes() == first
    config['engine']['defender_policy'] = 'evidence_v2'
    with pytest.raises(ValueError):
        execute(config, resume=True)


@pytest.mark.parametrize('change', [
    {'condition_status': 'contradicted'},
    {'condition_status': 'uncertain', 'inference_role': 'secondary'},
])
def test_contradiction_or_secondary_role_cannot_be_asserted_without_evidence(change):
    r = review()
    r['candidate_assessment'].update(change, premise_quote='', conclusion_quote='', evidence_quote='')
    with pytest.raises(ValueError, match='TARGET evidence'):
        aligned.validate_defender(r, TARGET, CANDIDATE)
