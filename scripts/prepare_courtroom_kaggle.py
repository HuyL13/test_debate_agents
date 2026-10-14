"""Restore pinned public data/tokenizer after cloning; no credentials needed."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.discourse_classification.data import load_records


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def download_verified(url, target, expected):
    target = Path(target)
    if target.exists():
        if sha(target.read_bytes()) != expected:
            raise ValueError(f'Existing artifact checksum differs: {target}')
        return
    with urllib.request.urlopen(url, timeout=120) as response:
        blob = response.read()
    if sha(blob) != expected:
        raise ValueError(f'Download checksum differs: {target.name}')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(blob)
    temporary.replace(target)


def serialize_pinned(rows, expected):
    text = json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    # Original flat artifacts were exported on Windows. Preserve their exact
    # checksum on Linux too, without changing text content or split membership.
    for candidate in (text.encode('utf8'), text.replace('\n', '\r\n').encode('utf8')):
        if sha(candidate) == expected:
            return candidate
    raise ValueError('Classification export checksum differs from pinned provenance')


def prepare_classification(root=ROOT, source_dir=None):
    root = Path(root)
    destination = root/'data/cocolofa/classification'
    provenance = json.loads((destination/'provenance.json').read_text(encoding='utf-8-sig'))
    for split, info in provenance['splits'].items():
        target = destination/f'{split}.json'
        if target.exists():
            if sha(target.read_bytes()) != info['sha256']:
                raise ValueError(f'Existing classification checksum differs: {split}')
            print(f'[DATA] {split}: verified {info["count"]} samples', flush=True)
            continue
        if source_dir is None:
            source = root/'data/cocolofa'/f'{split}.json'
            url = f'https://raw.githubusercontent.com/Crowd-AI-Lab/cocolofa/{provenance["commit"]}/{split}.json'
            download_verified(url, source, info['source_sha256'])
        else:
            source = Path(source_dir)/f'{split}.json'
            if sha(source.read_bytes()) != info['source_sha256']:
                raise ValueError(f'Upstream checksum differs: {split}')
        rows = load_records(source, 'paper')
        if len(rows) != info['count']:
            raise ValueError(f'Classification count differs: {split}')
        blob = serialize_pinned(rows, info['sha256'])
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(blob)
        temporary.replace(target)
        print(f'[DATA] {split}: prepared and verified {len(rows)} samples', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/courtroom_rl.kaggle.yaml')
    args = parser.parse_args()
    import yaml
    config = yaml.safe_load((ROOT/args.config).read_text(encoding='utf-8-sig'))
    prepare_classification()
    options = config['tokenizer']
    download_verified(options['source'], ROOT/options['path'], options['sha256'])
    print('[TOKENIZER] Pinned Llama3 tokenizer verified', flush=True)


if __name__ == '__main__':
    main()
