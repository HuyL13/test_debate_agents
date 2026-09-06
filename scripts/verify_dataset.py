import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.verify import verify_dataset
from src.io_utils import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default='data/cocolofa')
    parser.add_argument('--output', default='reports/dataset_verification.json')
    args = parser.parse_args()
    report = verify_dataset(args.data_dir)
    write_json(args.output, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
