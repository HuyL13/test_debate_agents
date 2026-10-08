"""Filter prepared upstream splits to eight labels without changing split membership."""
import argparse
import json
from collections import Counter
from pathlib import Path

from src.discourse_classification.data import load_records
from src.io_utils import file_hash, write_json


def prepare(data_dir=Path('data/cocolofa')):
    data_dir = Path(data_dir)
    destination = data_dir / 'classification'
    selected = {}
    for split in ('train', 'dev', 'test'):
        rows = load_records(data_dir / f'{split}.json', 'paper')
        target = destination / f'{split}.json'
        if target.exists() and json.loads(target.read_text(encoding='utf-8')) != rows:
            raise ValueError(f'Refusing to overwrite different data: {target}')
        selected[split] = rows
    destination.mkdir(parents=True, exist_ok=True)
    for split, rows in selected.items():
        target = destination / f'{split}.json'
        if not target.exists():
            write_json(target, rows)
    provenance = destination / 'provenance.json'
    if not provenance.exists():
        upstream = data_dir / 'provenance.json'
        origin = json.loads(upstream.read_text(encoding='utf-8')) if upstream.exists() else {}
        write_json(provenance, {
            'repository': origin.get('repository'), 'commit': origin.get('commit'),
            'transformation': 'Preserve upstream splits; remove none; retain original parent context.',
            'splits': {split: {'count': len(rows), 'label_counts': dict(Counter(r['gold'] for r in rows)),
                              'source_sha256': file_hash(data_dir / f'{split}.json'),
                              'sha256': file_hash(destination / f'{split}.json')}
                       for split, rows in selected.items()},
        })
    print('Classification: ' + ', '.join(f'{split}={len(rows)}' for split, rows in selected.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir', default='data/cocolofa')
    prepare(Path(ap.parse_args().data_dir))


if __name__ == '__main__':
    main()
