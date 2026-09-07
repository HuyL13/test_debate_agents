from scripts.full_benchmark import render


def test_comparison_does_not_publish_partial_run_scores(tmp_path):
    jobs = [{'task': task, 'mode': mode, 'completed': 10, 'expected': 798 if task == 'detection' else 481,
             'state': 'running', 'launches': 1}
            for task in ('detection', 'classification') for mode in ('single', 'adaptive')]
    target = tmp_path / 'comparison.md'
    render(jobs, target)
    own_rows = [line for line in target.read_text(encoding='utf-8').splitlines()
                if line.startswith('| gpt-oss')]
    assert len(own_rows) == 2
    assert all(line.count('pending') == 6 for line in own_rows)


def test_comparison_formats_complete_detection_independently(tmp_path):
    jobs = [{'task': task, 'mode': mode, 'completed': 0, 'expected': 798 if task == 'detection' else 481,
             'state': 'running', 'launches': 1}
            for task in ('detection', 'classification') for mode in ('single', 'adaptive')]
    jobs[0].update(state='complete', completed=798,
                   result={'precision': 0.5, 'recall': 0.75, 'f1': 0.6})
    target = tmp_path / 'comparison.md'
    render(jobs, target)
    assert '| 50.00 | 75.00 | 60.00 | pending | pending | pending |' in target.read_text(encoding='utf-8')
