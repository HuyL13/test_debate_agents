"""Export three exact pinned Git blobs, bypassing checkout newline conversion."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.io_utils import file_hash, write_json

PIN = 'c39d45fdd57401e1f6cb674f25113dfa0304e734'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='upstream/cocolofa')
    parser.add_argument('--dest', default='data/cocolofa')
    args = parser.parse_args()
    source, dest = Path(args.source), Path(args.dest)
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != PIN:
        parser.error(f'Expected upstream commit {PIN}, got {commit}; inspect and document before updating the pin')
    dest.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ('train.json', 'dev.json', 'test.json'):
        # Read the pinned blob directly: Windows checkouts may apply autocrlf.
        blob = subprocess.check_output(['git', '-C', str(source), 'show', f'{PIN}:{name}'])
        import hashlib
        expected = hashlib.sha256(blob).hexdigest()
        if (dest / name).exists() and file_hash(dest / name) != expected:
            parser.error(f'Refusing to overwrite different data: {dest / name}')
        if not (dest / name).exists():
            (dest / name).write_bytes(blob)
        hashes[name] = expected
    write_json(dest / 'provenance.json', {'repository': 'https://github.com/Crowd-AI-Lab/cocolofa',
                                        'commit': commit, 'sha256': hashes})
    print(json.dumps(hashes, indent=2))


if __name__ == '__main__':
    main()
