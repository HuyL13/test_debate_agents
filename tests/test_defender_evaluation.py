import json
from copy import deepcopy

import pytest

from src.data.loader import ModelInput
from src.io_utils import digest
from src.defender_experiment import ReplayClient, build_snapshot, validate_snapshot, stage_metrics


INPUT = ModelInput('Title', '', 'One bad shop proves every shop is bad.')
REPORT = {'has_fallacy_charge': True, 'candidate_class': 'Hasty Generalization',
          'quote': INPUT.comment, 'defect_mechanism': 'Sample leap.',
          'runner_up_class': 'Appeal to Majority', 'runner_up_quote': INPUT.comment,
          'runner_up_defect': 'Consensus.'}


def snapshot():
    return build_snapshot([('1', INPUT, REPORT)], dataset_hash='datahash', split='dev', context='paper')


def test_replay_returns_exact_report_without_calling_live_prosecutor():
    class NoAPI:
        def generate(self, **kw): raise AssertionError('live Prosecutor must never run')
    saved = snapshot()
    replay = ReplayClient(NoAPI(), saved)
    result = replay.generate(metadata={'role': 'Prosecutor', 'stage': 'indictment', 'sample_id': '1'},
                             user_prompt=json.dumps({'input': INPUT.as_dict()}), validator=None)
    assert result == REPORT
    result['quote'] = 'changed'
    assert saved['records'][0]['report'] == REPORT


@pytest.mark.parametrize('defect', ['missing', 'duplicate', 'context', 'quote'])
def test_snapshot_mismatch_fails_before_api(defect):
    saved = snapshot(); expected = {'1': INPUT}
    if defect == 'missing': expected['2'] = INPUT
    if defect == 'duplicate': saved['records'].append(deepcopy(saved['records'][0]))
    if defect == 'context': expected['1'] = ModelInput('Changed title', '', INPUT.comment)
    if defect == 'quote': saved['records'][0]['report']['quote'] = 'invented quote'
    saved['fingerprint'] = digest({k:v for k,v in saved.items() if k != 'fingerprint'})
    with pytest.raises(ValueError):
        validate_snapshot(saved, expected, dataset_hash='datahash', split='dev', context='paper')


def test_stage_metrics_distinguish_proposal_damage_from_final_protection():
    rows = [
        {'sample_id':'1','task':'classification','gold':'Hasty Generalization','status':'ok',
         'prosecutor':{'candidate_class':'Hasty Generalization'},
         'defender':{'concede_charge':False,'alternative_class':'False Dilemma'},
         'prediction':'Hasty Generalization'},
        {'sample_id':'2','task':'classification','gold':'False Dilemma','status':'ok',
         'prosecutor':{'candidate_class':'Hasty Generalization'},
         'defender':{'concede_charge':False,'alternative_class':'False Dilemma'},
         'prediction':'False Dilemma'},
    ]
    metrics = stage_metrics(rows)
    assert metrics['defender_counts']['beneficial'] == 1
    assert metrics['defender_counts']['harmful'] == 1
    assert metrics['final_counts']['beneficial'] == 1
    assert metrics['final_counts']['harmful'] == 0
    assert metrics['final']['accuracy'] == 1


def experiment_fixture(tmp_path, split='dev'):
    from src.runner import validate_config
    from src.io_utils import file_hash, write_json
    data = tmp_path/'data'; data.mkdir()
    path = data/(split+'.json')
    write_json(path, [{'sample_id':'1', 'title':'Title', 'comment':INPUT.comment,
                       'parent_comment':'', 'gold':'Hasty Generalization'}])
    saved = build_snapshot([('1', INPUT, REPORT)], dataset_hash=file_hash(path), split=split, context='paper')
    snap = tmp_path/'snapshot.json'; write_json(snap, saved)
    config = validate_config({'task':'classification', 'data_dir':str(data), 'split':split, 'context':'paper',
        'engine':{'adaptive_policy':'adversarial', 'defender_policy':'evidence_v2'},
        'model':{'provider':'mock', 'name':'offline-mock-v1', 'backoff_seconds':0},
        'output_dir':str(tmp_path/'out'), 'cache_dir':str(tmp_path/'cache')})
    return config, snap


def test_mock_v2_replay_runs_and_resumes_without_gold_in_requests(tmp_path):
    from src.defender_experiment import run_experiment
    config, snap = experiment_fixture(tmp_path)
    output = tmp_path/'out'
    summary = run_experiment(config, snap, output)
    assert summary['status'] == 'complete'
    assert summary['synthetic'] is True
    rows = [json.loads(l) for l in (output/'predictions.jsonl').read_text().splitlines()]
    assert rows[0]['prosecutor'] == REPORT
    assert rows[0]['defender_validation']['effective_decision'] == 'uphold'
    events = [json.loads(l) for l in (output/'raw_calls.jsonl').read_text().splitlines()]
    assert all(e['metadata']['role'] != 'Prosecutor' for e in events)
    for event in events:
        assert 'gold' not in event['metadata']
        request = json.loads(event['request']['messages'][1]['content'])
        assert set(request['input']) == {'title', 'parent_comment', 'comment'}
        assert 'gold' not in request
    before = (output/'raw_calls.jsonl').read_bytes()
    assert run_experiment(config, snap, output, resume=True)['status'] == 'complete'
    assert (output/'raw_calls.jsonl').read_bytes() == before
    config['engine']['defender_policy'] = 'diagnostic_v1'
    with pytest.raises(ValueError, match='identity'):
        run_experiment(config, snap, output, resume=True)


def test_test_replay_requires_matching_frozen_identity(tmp_path):
    from src.defender_experiment import run_experiment, prepare
    from src.io_utils import write_json
    config, snap = experiment_fixture(tmp_path, 'test')
    with pytest.raises(ValueError, match='requires --frozen'):
        run_experiment(config, snap, tmp_path/'out')
    frozen = tmp_path/'frozen.json'; write_json(frozen, prepare(config, snap)[2])
    config['model']['temperature'] = .6
    with pytest.raises(ValueError, match='frozen manifest differs'):
        run_experiment(config, snap, tmp_path/'out', frozen=frozen)
