import json
from pathlib import Path
from src.runner import load_config, experiment_identity, select_task, load_split, digest

args_config = 'configs/classification.adversarial.marketplace.yaml'
args_model = 'Llama-3.3-70B-Instruct'
args_output = 'outputs/marketplace-classification-adversarial-llama70b-dev66-v1'

config = load_config(args_config)
config['model']['name'] = args_model
config['output_dir'] = str(Path(args_output).resolve())

out_dir = Path(config['output_dir'])
experiment = experiment_identity(config)
split_name = config['split']
samples = select_task(load_split(Path(config['data_dir']) / f'{split_name}.json'), config['task'])
total = len(samples)
selection = {'sample_ids': [s.sample_id for s in samples],
             'gold': {s.sample_id: s.gold(config['task']) for s in samples},
             'scope': 'full_split' if len(samples) == total else 'subset', 'eligible_count': total}
identity = {'experiment': experiment, 'split': config['split'], 'selection': selection}
fingerprint = digest(identity)

manifest_path = out_dir / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
old_fp = manifest['run_fingerprint']
manifest.update(identity)
manifest['run_fingerprint'] = fingerprint
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Updated manifest.json: {old_fp} -> {fingerprint}')

# Update sample files
sample_files = list((out_dir / 'samples').glob('*.json'))
updated_samples = 0
for f in sample_files:
    data = json.loads(f.read_text(encoding='utf-8'))
    data['run_fingerprint'] = fingerprint
    f.write_text(json.dumps(data, indent=2), encoding='utf-8')
    updated_samples += 1

print(f'Updated {updated_samples} sample files to new fingerprint: {fingerprint}')
