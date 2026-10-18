"""Create an extraction manifest from local TRAIN only; never load test data."""
import json
from core import REPO, ROOT


def main():
    source = REPO / 'data/cocolofa/classification/train.json'
    rows = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('Expected a nonempty TRAIN sample list')
    required = {'sample_id', 'article_id', 'gold', 'comment'}
    if any(not required <= row.keys() for row in rows):
        raise ValueError('TRAIN rows require sample_id, article_id, gold, comment')
    if len({row['sample_id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate TRAIN sample IDs')
    samples = [{**row, 'split': 'induction'} for row in rows]
    destination = ROOT / 'full_train_manifest.json'
    destination.write_text(json.dumps({'samples': samples}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {len(samples)} TRAIN samples: {destination}')


if __name__ == '__main__':
    main()
