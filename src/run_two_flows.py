"""Paired dev experiments: A1/B1 without debate, then A2/B2 with the same planner budget."""
import argparse
from copy import deepcopy
from pathlib import Path

from src.io_utils import read_jsonl, write_json
from src.runner import execute, load_config


def compare(runs):
    indexed = {name: {row['sample_id']: row for row in rows} for name, rows in runs.items()}
    keys = set(indexed['A1'])
    if not keys or any(set(rows) != keys for rows in indexed.values()):
        raise ValueError('Comparison requires identical nonempty sample selections')
    comparisons = []
    for sample_id in sorted(keys):
        rows = {name: records[sample_id] for name, records in indexed.items()}
        if any(row['status'] != 'ok' for row in rows.values()):
            raise ValueError('Cannot compare incomplete runs')
        if len({(row['task'], row['gold']) for row in rows.values()}) != 1:
            raise ValueError('Task or gold mismatch')
        gold = rows['A1']['gold']
        entry = {'sample_id': sample_id, 'gold': gold, 'runs': {}, 'debate_effect': {}}
        for name, row in rows.items():
            entry['runs'][name] = {'prediction': row['prediction'], 'correct': row['prediction'] == gold,
                                   'initial_agents': row['initial_agents'], 'arbiter': row['arbiter']}
        for flow in ('A', 'B'):
            before, after = (rows[flow + str(stage)]['prediction'] == gold for stage in (1, 2))
            entry['debate_effect'][flow] = ('unchanged_correct' if after else 'unchanged_wrong') if before == after else (
                'fixed' if after else 'regressed')
        comparisons.append(entry)
    return comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=('detection', 'classification'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = Path(args.output).resolve()
    configs = {flow: load_config(f'configs/{args.task}.simplified_{flow.lower()}.yaml') for flow in ('A', 'B')}
    runs, summaries = {}, {}
    for stage in (1, 2):
        for flow in ('A', 'B'):
            name = flow + str(stage)
            config = deepcopy(configs[flow])
            config['engine']['mode'] = 'no_deliberation' if stage == 1 else 'adaptive'
            config['output_dir'] = str(root / name)
            summaries[name] = execute(config, limit=args.limit, resume=args.resume)
            if summaries[name]['status'] != 'complete':
                raise RuntimeError(f'{name} incomplete; fix the failure and use --resume')
            runs[name] = list(read_jsonl(root / name / 'predictions.jsonl'))
            write_json(root / name / 'predictions.pretty.json', runs[name])
    write_json(root / 'comparison.json', {'summaries': summaries, 'samples': compare(runs)})


if __name__ == '__main__':
    main()
