import json
from pathlib import Path

import pytest

from src.runner import execute, evaluate_run, freeze, load_config
from src.io_utils import read_jsonl


@pytest.fixture
def config(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    for split, aid in [('train', 1), ('dev', 2), ('test', 3)]:
        articles = [{'id': aid, 'title': 'Title', 'content': '<p>News</p>', 'comments': [
            {'id': f'{aid}1', 'news_id': aid, 'fallacy': 'none', 'respond_to': '', 'comment': 'Parent'},
            {'id': f'{aid}2', 'news_id': aid, 'fallacy': 'false dilemma', 'respond_to': f'{aid}1',
             'comment': 'Only these two choices exist.'}]}]
        (data_dir / f'{split}.json').write_text(json.dumps(articles), encoding='utf-8')
    return {'task': 'detection', 'data_dir': str(data_dir), 'split': 'dev', 'context': 'paper',
            'engine': {'mode': 'adaptive', 'protocol': 'round_robin', 'max_rounds': 2, 'early_stop': True},
            'model': {'name': 'fixture', 'provider': 'mock'}, 'output_dir': str(tmp_path / 'run'),
            'cache_dir': str(tmp_path / 'cache')}


def test_runner_writes_complete_trace_and_resume_makes_no_new_calls(config):
    result = execute(config)
    assert result['status'] == 'complete'
    assert result['synthetic'] is True
    path = Path(config['output_dir'])
    predictions = read_jsonl(path / 'predictions.jsonl')
    assert len(predictions) == 2
    assert {r['gold'] for r in predictions} == {'Fallacious', 'Non-Fallacious'}
    assert all('initial_agents' in r and 'arbiter' in r for r in predictions)
    audit_before = (path / 'raw_calls.jsonl').read_bytes()
    execute(config, resume=True)
    assert (path / 'raw_calls.jsonl').read_bytes() == audit_before
    assert evaluate_run(path / 'predictions.jsonl')['count'] == 2


def test_classification_runner_is_independent_and_filters_only_gold(config):
    config['task'] = 'classification'
    execute(config)
    rows = read_jsonl(Path(config['output_dir']) / 'predictions.jsonl')
    assert len(rows) == 1
    assert rows[0]['gold'] == 'False Dilemma'
    assert rows[0]['sample_id'] == '2:22'


def test_output_overwrite_and_changed_resume_rejected(config):
    execute(config)
    with pytest.raises(ValueError, match='exists'):
        execute(config)
    config['context'] = 'comment_only'
    with pytest.raises(ValueError, match='manifest'):
        execute(config, resume=True)


def test_test_split_requires_frozen_matching_experiment(config, tmp_path):
    config['split'] = 'test'
    with pytest.raises(ValueError, match='frozen'):
        execute(config)
    path = tmp_path / 'frozen.json'
    freeze(config, path)
    assert execute(config, frozen=path)['status'] == 'complete'
    config['engine']['max_rounds'] = 3
    with pytest.raises(ValueError, match='frozen'):
        execute(config, frozen=path, resume=True)


def test_evaluate_rejects_partial_and_tampered_gold(config):
    execute(config)
    path = Path(config['output_dir']) / 'predictions.jsonl'
    rows = read_jsonl(path)
    path.write_text(json.dumps(rows[0]) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='coverage'):
        evaluate_run(path)
    rows[0]['gold'] = 'Fallacious'
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='gold'):
        evaluate_run(path)


def test_partial_selection_labeled_subset_not_full_benchmark(config):
    result = execute(config, limit=1)
    assert result['selection_scope'] == 'subset'
    assert result['direct_comparison_candidate'] is False


def test_config_rejects_unknown_keys(tmp_path):
    path = tmp_path / 'broken.yaml'
    path.write_text('task: detection\nunknown_typo: true\n', encoding='utf-8')
    with pytest.raises(ValueError):
        load_config(path)


def test_cross_split_article_leakage_aborts_before_inference(config):
    data = Path(config['data_dir'])
    (data / 'test.json').write_bytes((data / 'dev.json').read_bytes())
    with pytest.raises(ValueError, match='Cross-split'):
        execute(config)
    assert not Path(config['output_dir']).exists()


def test_failure_is_incomplete_and_resume_retries_failed_sample(config, monkeypatch):
    from src.llm.mock import MockTransport
    original = MockTransport.complete

    def fail(self, payload):
        raise RuntimeError('Injected provider outage')

    monkeypatch.setattr(MockTransport, 'complete', fail)
    result = execute(config)
    assert result['status'] == 'incomplete'
    assert result['metrics'] is None
    assert result['failed_samples'] == ['2:21']
    monkeypatch.setattr(MockTransport, 'complete', original)
    result = execute(config, resume=True)
    assert result['status'] == 'complete'
    assert result['count'] == 2


def test_cached_replay_preserves_predictions_and_reports_zero_new_api_calls(config):
    first = execute(config)
    config['output_dir'] += '-replay'
    second = execute(config)
    assert second['usage']['api_calls'] == 0
    assert second['usage']['cache_hits'] > 0
    assert second['confusion_matrix'] == first['confusion_matrix']


def test_damaged_manifest_cannot_relabel_partial_run_as_complete(config):
    execute(config)
    directory = Path(config['output_dir'])
    path = directory / 'manifest.json'
    manifest = json.loads(path.read_text())
    del manifest['selection']['gold']['2:21']
    path.write_text(json.dumps(manifest))
    predictions = directory / 'predictions.jsonl'
    rows = read_jsonl(predictions)
    predictions.write_text(json.dumps(rows[1]) + '\n')
    with pytest.raises(ValueError, match='manifest'):
        evaluate_run(predictions)
    with pytest.raises(ValueError, match='manifest'):
        execute(config, resume=True)


def test_resume_quarantines_partial_final_audit_record(config):
    execute(config)
    directory = Path(config['output_dir'])
    audit = directory / 'raw_calls.jsonl'
    with audit.open('ab') as stream:
        stream.write(b'{"timestamp":"interrupted')
    result = execute(config, resume=True)
    assert result['status'] == 'complete'
    assert result['usage']['missing_usage_responses'] == 1
    assert len(list(directory.glob('raw_calls.interrupted.*.bin'))) == 1
    assert read_jsonl(audit)


def test_interior_audit_corruption_is_rejected(config):
    execute(config)
    audit = Path(config['output_dir']) / 'raw_calls.jsonl'
    audit.write_bytes(b'{broken}\n' + audit.read_bytes())
    with pytest.raises(ValueError, match='audit'):
        execute(config, resume=True)
