"""Compare completed exact-replay runs; gold stays in this offline evaluator."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.game_evaluation import compare_replays
from src.io_utils import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output')
    parser.add_argument('--benefit', type=float, default=1.0)
    parser.add_argument('--harm', type=float, default=1.0)
    parser.add_argument('--token-penalty', type=float, default=0.0)
    args = parser.parse_args()
    try:
        if args.output and Path(args.output).exists():
            raise ValueError('Output exists; choose a new versioned report path')
        result = compare_replays(args.baseline, args.candidate, benefit=args.benefit,
                                 harm=args.harm, token_penalty=args.token_penalty)
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
