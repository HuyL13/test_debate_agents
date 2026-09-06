"""Exercise all six engine settings per task on real dev inputs, with zero API calls."""
import argparse
import contextlib
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.io_utils import write_json
from src.runner import execute, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--report', default='reports/smoke_results.json')
    parser.add_argument('--output-root', default='outputs/smoke-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    args = parser.parse_args()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    with (output_root / 'progress.log').open('w', encoding='utf-8') as log:
        for task in ('detection', 'classification'):
            settings = [('single', 'round_robin'), ('no_deliberation', 'round_robin'),
                        ('fixed', 'round_robin'), ('fixed', 'point_counterpoint'),
                        ('fixed', 'cross_examination'), ('adaptive', 'round_robin')]
            for mode, protocol in settings:
                config = load_config(f'configs/{task}.yaml')
                config['model'].update(provider='mock', name='offline-mock-v1')
                config['engine'].update(mode=mode, protocol=protocol)
                config['output_dir'] = str(output_root / f'{task}-{mode}-{protocol}')
                with contextlib.redirect_stdout(log):
                    summary = execute(config, limit=args.limit)
                results.append({'task': task, 'mode': mode, 'fixed_protocol': protocol if mode == 'fixed' else None,
                                'count': summary.get('count'), 'status': summary['status'],
                                'synthetic': True, 'usage': summary['usage'],
                                'output': str(Path(config['output_dir']).relative_to(Path.cwd()))})
                print(task, mode, protocol, summary['status'], flush=True)
    report = {'purpose': 'Offline plumbing verification; NOT model benchmark results',
              'api_key_required': False, 'synthetic': True, 'runs': results}
    write_json(args.report, report)
    return 0 if all(r['status'] == 'complete' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
