import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.runner import freeze, load_config


def main():
    parser = argparse.ArgumentParser(description='Freeze prompts, source, config, dependency versions and data hashes before test')
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mock', action='store_true')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.mock:
        config['model'].update(provider='mock', name='offline-mock-v1')
    elif config['model']['name'] == 'SET_MODEL_SNAPSHOT':
        parser.error('Set model.name before freezing a real experiment')
    result = freeze(config, args.output)
    print(result['experiment']['fingerprint'])


if __name__ == '__main__':
    main()
