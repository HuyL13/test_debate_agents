import json
import threading
import time

import pytest

from src.discourse_classification.runner import execute


def test_parallel_runner_serializes_parser_and_writes_all_results_once(tmp_path, monkeypatch):
    import src.discourse_classification.runner as runner
    data = tmp_path / 'input.json'
    rows = [{'sample_id': str(i), 'article_id': i, 'comment': f'Natural item {i}.', 'gold': 'Appeal to Nature'} for i in range(3)]
    data.write_text(json.dumps(rows))
    barrier = threading.Barrier(3, timeout=3)
    state = {'active': 0, 'calls': 0}
    guard = threading.Lock()

    def parser(text):
        with guard:
            assert state['active'] == 0, 'Parser cannot run concurrently'
            state['active'] += 1
        time.sleep(.01)
        with guard:
            state['active'] -= 1

    def classify(client, sources, sid, **kwargs):
        kwargs['parser'](sources['comment'])
        barrier.wait()
        with guard:
            state['calls'] += 1
        assert kwargs['demo_exclusions'] == {0, 1, 2}
        return {'label': 'Appeal to Nature', 'primary_prediction': 'Appeal to Nature',
                'decision_mode': 'role_match', 'candidates': []}

    monkeypatch.setattr(runner, 'classify', classify)
    config = {'input': str(data), 'model': {}, 'method': 'graph', 'workers': 3,
              'output_root': str(tmp_path / 'runs')}
    result = execute(config, output='parallel', client=object(), parser=parser)
    assert result['ok'] == 3 and result['errors'] == 0
    persisted = [json.loads(line) for line in (tmp_path / 'runs/parallel/results.jsonl').read_text().splitlines()]
    assert [r['sample_id'] for r in persisted] == ['0', '1', '2']
    execute(config, output='parallel', client=object(), parser=parser, resume=True)
    assert state['calls'] == 3


@pytest.mark.parametrize('workers', [0, True, 9, 2.5])
def test_invalid_worker_count_is_rejected_before_loading_data(workers):
    with pytest.raises(ValueError, match='workers'):
        execute({'workers': workers})
