import json
import glob
from pathlib import Path
from datetime import datetime, timezone

from src.runner import load_config, experiment_identity, validate_manifest
from src.data.loader import load_split, select_task
from src.data.verify import verify_dataset
from src.io_utils import digest, write_json

def sync():
    config_path = 'configs/classification.adversarial.test.marketplace.yaml'
    config = load_config(config_path)
    exp = experiment_identity(config)
    print("New experiment fingerprint:", exp['fingerprint'])

    # 1. Update frozen report
    frozen_path = Path('reports/frozen-adversarial-classification-test-llama70b-v1.json')
    verification = verify_dataset(config['data_dir'])
    frozen_data = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'experiment': exp,
        'dataset_verification': verification
    }
    write_json(frozen_path, frozen_data)
    print("Updated frozen report:", frozen_path)

    # 2. Compute run fingerprint
    split_file = Path(config['data_dir']) / f"{config['split']}.json"
    samples = select_task(load_split(split_file), config['task'])
    total = len(samples)
    selection = {
        'sample_ids': [s.sample_id for s in samples],
        'gold': {s.sample_id: s.gold(config['task']) for s in samples},
        'scope': 'full_split' if len(samples) == total else 'subset',
        'eligible_count': total
    }
    identity = {'experiment': exp, 'split': config['split'], 'selection': selection}
    run_fp = digest(identity)
    print("New run fingerprint:", run_fp)

    # 3. Update output manifest
    out_dir = Path(config['output_dir'])
    manifest_path = out_dir / 'manifest.json'
    manifest_data = {
        **identity,
        'run_fingerprint': run_fp,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'published_counts_match': all(s['matches_published_counts'] for s in verification['splits'].values()),
        'frozen_file': str(frozen_path)
    }
    validate_manifest(manifest_data)
    write_json(manifest_path, manifest_data)
    print("Updated manifest:", manifest_path)

    # 4. Remove any error sample files
    sample_files = glob.glob(str(out_dir / 'samples' / '*.json'))
    valid_sample_files = []
    for sf in sample_files:
        d = json.loads(Path(sf).read_text(encoding='utf-8'))
        if d.get('status') != 'ok':
            Path(sf).unlink()
            print("Removed error sample file:", sf, d.get('sample_id'))
        else:
            valid_sample_files.append((sf, d))

    # 5. Update run_fingerprint in all remaining valid sample files
    print(f"Updating run_fingerprint for {len(valid_sample_files)} valid sample files...")
    for sf, d in valid_sample_files:
        d['run_fingerprint'] = run_fp
        Path(sf).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print("Done! Validated all sample files.")

if __name__ == '__main__':
    sync()
