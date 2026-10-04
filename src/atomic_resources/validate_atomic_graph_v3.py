"""CLI validator for v3 graph JSON and its original source text file."""
import argparse
import json
from pathlib import Path

from src.atomic_v3 import validate_graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('source')
    args = parser.parse_args()
    obj = json.loads(Path(args.graph).read_text(encoding='utf-8'))
    validate_graph(obj, Path(args.source).read_text(encoding='utf-8'))
    print('VALID: v3 structure, exact source trace, IDs, scope groups and SUPPORT DAG')


if __name__ == '__main__':
    main()
