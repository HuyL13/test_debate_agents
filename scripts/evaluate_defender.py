"""Snapshot, freeze and run paired Defender experiments without live Prosecutor calls."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.runner import load_config
from src.io_utils import write_json
from src.defender_experiment import export_snapshot, prepare, run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['snapshot', 'freeze', 'run'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--split', choices=['dev', 'test', 'train'])
    parser.add_argument('--predictions')
    parser.add_argument('--snapshot')
    parser.add_argument('--output', required=True)
    parser.add_argument('--frozen')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--mock', action='store_true')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.split: config['split'] = args.split
        if args.mock: config['model'].update(provider='mock', name='offline-mock-v1')
        if args.action == 'snapshot':
            if not args.predictions: raise ValueError('snapshot requires --predictions')
            value = export_snapshot(config, args.predictions, args.output)
        elif args.action == 'freeze':
            if not args.snapshot: raise ValueError('freeze requires --snapshot')
            if Path(args.output).exists(): raise ValueError('Frozen output already exists')
            value = prepare(config, args.snapshot, args.limit)[2]
            write_json(args.output, value)
        else:
            if not args.snapshot: raise ValueError('run requires --snapshot')
            value = run_experiment(config, args.snapshot, args.output, limit=args.limit,
                                   resume=args.resume, frozen=args.frozen)
        print(json.dumps(value if args.action=='run' else {'fingerprint':value['fingerprint']}, indent=2))
        return int(value.get('status') == 'incomplete')
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
