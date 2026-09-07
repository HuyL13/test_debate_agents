"""Run manifests, frozen experiments, resumable inference and coverage-checked scoring."""
import argparse
import json
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import yaml

from src.data.loader import load_split, select_task
from src.data.verify import PINNED_HASHES, verify_dataset
from src.engine import Engine
from src.evaluate import score
from src.io_utils import digest, file_hash, read_jsonl, recover_audit_tail, write_json
from src.labels import labels_for
from src.llm.client import Client, ModelConfig

ROOT = Path(__file__).resolve().parents[1]
CONFIG_KEYS = {'task', 'data_dir', 'split', 'context', 'engine', 'model', 'output_dir', 'cache_dir'}
ENGINE_DEFAULTS = {'mode': 'adaptive', 'protocol': 'round_robin', 'max_rounds': 3, 'early_stop': True,
                   'adaptive_policy': 'planner'}


def validate_config(config):
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError(f'Config must contain exactly: {sorted(CONFIG_KEYS)}')
    labels_for(config['task'])
    if config['split'] not in ('train', 'dev', 'test') or config['context'] not in ('paper', 'article', 'comment_only'):
        raise ValueError('Unknown split or context setting')
    if not isinstance(config['engine'], dict) or set(config['engine']) - set(ENGINE_DEFAULTS):
        raise ValueError('Unknown engine option')
    engine = {**ENGINE_DEFAULTS, **config['engine']}
    if type(engine['early_stop']) is not bool:
        raise ValueError('early_stop must be boolean')
    Engine(None, task=config['task'], **engine)
    if not isinstance(config['model'], dict):
        raise ValueError('model must be a mapping')
    try:
        model = ModelConfig(**config['model'])
    except TypeError as exc:
        raise ValueError(f'Invalid model configuration: {exc}') from exc
    for key in ('data_dir', 'output_dir', 'cache_dir'):
        if not isinstance(config[key], str) or not config[key]:
            raise ValueError(f'{key} must be a path string')
    return {**config, 'engine': engine, 'model': asdict(model)}


def load_config(path):
    path = Path(path).resolve()
    config = validate_config(yaml.safe_load(path.read_text(encoding='utf-8')))
    # Bundled configs live in configs/. All relative paths are project-root relative.
    base = path.parent.parent
    for key in ('data_dir', 'output_dir', 'cache_dir'):
        value = Path(config[key])
        config[key] = str(value if value.is_absolute() else (base / value).resolve())
    return config


def experiment_identity(config):
    semantic = {key: config[key] for key in ('task', 'context', 'engine', 'model')}
    datasets = {split: file_hash(Path(config['data_dir']) / f'{split}.json') for split in ('train', 'dev', 'test')}
    source = {str(path.relative_to(ROOT)).replace('\\', '/'): file_hash(path)
              for folder in ('src', 'scripts') for path in sorted((ROOT / folder).rglob('*.py'))}
    environment = {'python': platform.python_version(), 'PyYAML': version('PyYAML'), 'jsonschema': version('jsonschema')}
    identity = {'config': semantic, 'dataset_hashes': datasets, 'source_hashes': source, 'environment': environment}
    return {'fingerprint': digest(identity), **identity}


def freeze(config, path):
    config = validate_config(config)
    if Path(path).exists():
        raise ValueError('Frozen file exists; choose a new versioned path')
    verification = verify_dataset(config['data_dir'])
    result = {'created_at': datetime.now(timezone.utc).isoformat(),
              'experiment': experiment_identity(config), 'dataset_verification': verification}
    write_json(path, result)
    return result


def _trace_path(directory, sample_id):
    return Path(directory) / 'samples' / (digest(sample_id) + '.json')


def _export_predictions(directory, sample_ids):
    target = Path(directory) / 'predictions.jsonl'
    temporary = target.with_suffix('.jsonl.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        for sid in sample_ids:
            path = _trace_path(directory, sid)
            if path.exists():
                stream.write(json.dumps(json.loads(path.read_text(encoding='utf-8')), ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(target)
    return target


def _audit_usage(directory, model_config):
    path = Path(directory) / 'raw_calls.jsonl'
    usage = {'api_calls': 0, 'cache_hits': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
             'total_tokens': 0, 'provider_cached_tokens': 0, 'missing_usage_responses': 0}
    models = set()
    usage['missing_usage_responses'] = len(list(Path(directory).glob('raw_calls.interrupted.*.bin')))
    from src.llm.client import accumulate_usage, estimate_cost
    if path.exists():
        for event in read_jsonl(path):
            response = event.get('response', {})
            if event.get('cache_hit'):
                usage['cache_hits'] += 1
            else:
                usage['api_calls'] += 1
                if 'response' in event:
                    accumulate_usage(usage, response.get('usage'))
            if response.get('model'):
                models.add(response['model'])
    return {'usage': usage, 'model_versions': sorted(models),
            'estimated_cost_usd': estimate_cost(ModelConfig(**model_config), usage),
            'cost_note': 'Configured token-rate estimate for recorded responses; not a provider invoice.'}


def validate_manifest(manifest):
    try:
        experiment = manifest['experiment']
        body = {k: v for k, v in experiment.items() if k != 'fingerprint'}
        identity = {key: manifest[key] for key in ('experiment', 'split', 'selection')}
        if digest(body) != experiment['fingerprint'] or digest(identity) != manifest['run_fingerprint']:
            raise ValueError('Fingerprint mismatch')
        selection = manifest['selection']
        ids, gold = selection['sample_ids'], selection['gold']
        if not ids or len(ids) != len(set(ids)) or set(ids) != set(gold):
            raise ValueError('Selection IDs and gold mapping differ')
        count = selection['eligible_count']
        if type(count) is not int or count < len(ids):
            raise ValueError('Invalid eligible count')
        expected_scope = 'full_split' if len(ids) == count else 'subset'
        if selection['scope'] != expected_scope:
            raise ValueError('Invalid selection scope')
        if manifest['split'] not in ('train', 'dev', 'test'):
            raise ValueError('Invalid split')
        if any(label not in labels_for(experiment['config']['task']) for label in gold.values()):
            raise ValueError('Invalid gold label')
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'Invalid run manifest: {exc}') from exc


def evaluate_run(predictions):
    predictions = Path(predictions)
    manifest_path = predictions.parent / 'manifest.json'
    if not manifest_path.exists():
        raise ValueError('Evaluation requires the sibling run manifest.json to verify coverage')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    validate_manifest(manifest)
    rows = read_jsonl(predictions)
    expected = manifest['selection']['gold']
    if len(rows) != len(expected) or {row['sample_id'] for row in rows} != set(expected):
        raise ValueError('Prediction coverage does not match the selected sample manifest')
    for row in rows:
        if row.get('run_fingerprint') != manifest['run_fingerprint']:
            raise ValueError('Prediction belongs to a different run manifest')
        if row['task'] != manifest['experiment']['config']['task'] or row['gold'] != expected[row['sample_id']]:
            raise ValueError('Task/gold differs from the selected sample manifest')
    result = score(rows)
    semantic = manifest['experiment']['config']
    synthetic = semantic['model']['provider'] == 'mock'
    full = manifest['selection']['scope'] == 'full_split'
    result.update(status='complete', synthetic=synthetic, selection_scope=manifest['selection']['scope'],
                  split=manifest['split'], context=semantic['context'],
                  mode=semantic['engine']['mode'], run_fingerprint=manifest['run_fingerprint'],
                  direct_comparison_candidate=(not synthetic and full and manifest['split'] == 'test'
                                               and semantic['context'] == 'paper'
                                               and manifest['experiment']['dataset_hashes'] == PINNED_HASHES))
    result.update(_audit_usage(predictions.parent, semantic['model']))
    return result


def execute(config, *, limit=None, resume=False, frozen=None):
    config = validate_config(config)
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be a positive integer')
    verification = verify_dataset(config['data_dir'])
    experiment = experiment_identity(config)
    if config['split'] == 'test':
        if frozen is None:
            raise ValueError('Test runs require --frozen from scripts/freeze_experiment.py')
        saved = json.loads(Path(frozen).read_text(encoding='utf-8'))
        if saved['experiment'] != experiment:
            raise ValueError('Current experiment differs from the frozen manifest')
    samples = select_task(load_split(Path(config['data_dir']) / f'{config["split"]}.json'), config['task'])
    total = len(samples)
    if limit is not None:
        samples = samples[:limit]
    if not samples:
        raise ValueError('No eligible samples')
    selection = {'sample_ids': [s.sample_id for s in samples],
                 'gold': {s.sample_id: s.gold(config['task']) for s in samples},
                 'scope': 'full_split' if len(samples) == total else 'subset', 'eligible_count': total}
    identity = {'experiment': experiment, 'split': config['split'], 'selection': selection}
    fingerprint = digest(identity)
    directory = Path(config['output_dir'])
    path = directory / 'manifest.json'
    if path.exists():
        if not resume:
            raise ValueError('Output exists; use --resume or choose a new --output directory')
        saved = json.loads(path.read_text(encoding='utf-8'))
        validate_manifest(saved)
        if saved.get('run_fingerprint') != fingerprint:
            raise ValueError('Resume manifest differs from this config/data/source/selection')
    else:
        if directory.exists() and any(directory.iterdir()):
            raise ValueError('Output directory exists without a compatible manifest')
        directory.mkdir(parents=True, exist_ok=True)
        write_json(path, {**identity, 'run_fingerprint': fingerprint,
                          'created_at': datetime.now(timezone.utc).isoformat(),
                          'published_counts_match': all(s['matches_published_counts'] for s in verification['splits'].values()),
                          'frozen_file': str(frozen) if frozen else None})
    if resume:
        recover_audit_tail(directory / 'raw_calls.jsonl')
    model = ModelConfig(**config['model'])
    client = Client(model, Path(config['cache_dir']) / 'responses.sqlite', directory / 'raw_calls.jsonl')
    engine = Engine(client, task=config['task'], **config['engine'])
    errors = []
    for index, sample in enumerate(samples, 1):
        trace_path = _trace_path(directory, sample.sample_id)
        prior = {}
        if resume and trace_path.exists():
            prior = json.loads(trace_path.read_text(encoding='utf-8'))
            if prior.get('run_fingerprint') != fingerprint or prior.get('gold') != sample.gold(config['task']):
                raise ValueError('Stored trace differs from run manifest')
            if prior.get('status') == 'ok':
                continue
        base = {'sample_id': sample.sample_id, 'article_id': sample.article_id, 'task': config['task'],
                'split': config['split'], 'gold': sample.gold(config['task']), 'run_fingerprint': fingerprint,
                'missing_parent': sample.missing_parent, 'synthetic': model.provider == 'mock'}
        before = client.usage.copy()
        client.model_versions = set()
        try:
            result = engine.run(sample.model_input(config['context']),
                                {'dataset': experiment['dataset_hashes'][config['split']],
                                 'split': config['split'], 'sample_id': sample.sample_id,
                                 'experiment': experiment['fingerprint']})
            trace = {**base, **result, 'status': 'ok'}
        except Exception as exc:
            trace = {**base, 'status': 'error', 'prediction': None,
                     'error': f'{type(exc).__name__}: {exc}'}
            errors.append(sample.sample_id)
        trace['token_usage'] = {k: client.usage[k] - before[k] + prior.get('token_usage', {}).get(k, 0) for k in before}
        trace['model_versions'] = sorted(client.model_versions | set(prior.get('model_versions', [])))
        write_json(trace_path, trace)
        print(f'[{index}/{len(samples)}] {sample.sample_id}: {trace["status"]}', flush=True)
        if trace['status'] == 'error':
            # Stop at the first failure; no cascading paid failures or dropped examples.
            break
    predictions = _export_predictions(directory, selection['sample_ids'])
    if errors:
        summary = {'status': 'incomplete', 'failed_samples': errors,
                   'synthetic': model.provider == 'mock', 'metrics': None,
                   **_audit_usage(directory, config['model'])}
    else:
        summary = evaluate_run(predictions)
    write_json(directory / 'summary.json', summary)
    return summary


def cli(task):
    parser = argparse.ArgumentParser(description=f'Run CoCoLoFa {task}')
    parser.add_argument('--config', default=f'configs/{task}.yaml')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--split', choices=('train', 'dev', 'test'))
    parser.add_argument('--output')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--mock', action='store_true', help='Offline plumbing test; never a real benchmark')
    parser.add_argument('--frozen')
    parser.add_argument('--mode', choices=('single', 'no_deliberation', 'fixed', 'adaptive'))
    parser.add_argument('--protocol', choices=('round_robin', 'point_counterpoint', 'cross_examination'))
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if config['task'] != task:
            raise ValueError('Config task does not match runner')
        if args.mock:
            config['model'].update(provider='mock', name='offline-mock-v1')
        elif config['model']['name'] == 'SET_MODEL_SNAPSHOT':
            raise ValueError('Set model.name in the YAML to your accessible API model snapshot')
        for field in ('split',):
            if getattr(args, field):
                config[field] = getattr(args, field)
        if args.output:
            config['output_dir'] = str(Path(args.output).resolve())
        for field in ('mode', 'protocol'):
            if getattr(args, field):
                config['engine'][field] = getattr(args, field)
        summary = execute(config, limit=args.limit, resume=args.resume, frozen=args.frozen)
        print(json.dumps(summary, indent=2))
        return 0 if summary['status'] == 'complete' else 1
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f'Error: {exc}\n')
