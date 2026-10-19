import json
from pathlib import Path
from src.runner import load_config, experiment_identity, digest, select_task
from src.data.loader import load_split

cfg = load_config('configs/classification.adversarial.nvidia.yaml')
cfg['model']['name'] = 'meta/llama-3.2-11b-vision-instruct'
cfg['output_dir'] = 'outputs/nvidia-classification-adversarial-llama11b-dev66-v4'

output_dir = Path(cfg['output_dir'])
manifest_path = output_dir / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

data_file = Path(cfg['data_dir']) / (cfg['split'] + '.json')
samples = select_task(load_split(data_file), cfg['task'])
selection = {
    'sample_ids': [s.sample_id for s in samples],
    'gold': {s.sample_id: s.gold(cfg['task']) for s in samples},
    'scope': 'full_split',
    'eligible_count': len(samples)
}
exp = experiment_identity(cfg)
identity = {'experiment': exp, 'split': cfg['split'], 'selection': selection}
new_fp = digest(identity)

print(f"Old fingerprint: {manifest.get('run_fingerprint')}")
print(f"New fingerprint: {new_fp}")

# Update manifest
manifest['experiment'] = exp
manifest['run_fingerprint'] = new_fp
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print("Updated manifest.json")

# Update samples
samples_dir = output_dir / 'samples'
count_updated = 0
for p in samples_dir.glob('*.json'):
    data = json.loads(p.read_text(encoding='utf-8'))
    # Delete failed trace for 133:3846 so runner re-runs it cleanly
    if data.get('status') == 'error' or data.get('sample_id') == '133:3846':
        p.unlink()
        print(f"Removed failed trace: {p.name} ({data.get('sample_id')})")
        continue
    data['run_fingerprint'] = new_fp
    p.write_text(json.dumps(data, indent=2), encoding='utf-8')
    count_updated += 1

print(f"Successfully updated {count_updated} sample traces to new fingerprint.")
