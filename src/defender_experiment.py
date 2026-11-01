"""Paired Defender experiments with immutable, label-free Prosecutor snapshots."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json

from src.adversarial_schemas import prosecutor_schema, validate_prosecutor
from src.data.loader import load_split, select_task
from src.engine import Engine
from src.evaluate import score
from src.io_utils import digest, file_hash, read_jsonl, write_json, append_jsonl, recover_audit_tail
from src.llm.client import Client, ModelConfig
from src.schemas import validate_output


def _check_report(report, target):
    validate_output(report, prosecutor_schema('classification'))
    validate_prosecutor(deepcopy(report), target, 'classification')


def build_snapshot(records, *, dataset_hash, split, context):
    rows = []
    for sid, model_input, report in records:
        _check_report(report, model_input.comment)
        rows.append({'sample_id': sid, 'input_hash': digest(model_input.as_dict()), 'report': deepcopy(report)})
    if not rows or len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Snapshot requires nonempty unique sample IDs')
    body = {'version': 1, 'dataset_hash': dataset_hash, 'split': split, 'context': context, 'records': rows}
    return {**body, 'fingerprint': digest(body)}


def validate_snapshot(snapshot, inputs, *, dataset_hash, split, context):
    if snapshot.get('fingerprint') != digest({k:v for k,v in snapshot.items() if k != 'fingerprint'}):
        raise ValueError('Snapshot fingerprint mismatch')
    if snapshot.get('version') != 1 or any(snapshot.get(k) != v for k,v in
        [('dataset_hash', dataset_hash), ('split', split), ('context', context)]):
        raise ValueError('Snapshot dataset/split/context mismatch')
    records = snapshot['records']
    ids = [r['sample_id'] for r in records]
    if not ids or len(ids) != len(set(ids)) or set(ids) != set(inputs):
        raise ValueError('Snapshot missing or duplicate sample IDs')
    for record in records:
        model_input = inputs[record['sample_id']]
        if record['input_hash'] != digest(model_input.as_dict()):
            raise ValueError('Snapshot context/input mismatch')
        _check_report(record['report'], model_input.comment)


class ReplayClient:
    def __init__(self, client, snapshot, audit_path=None):
        self.client = client
        self.records = {r['sample_id']: deepcopy(r) for r in snapshot['records']}
        self.audit_path = audit_path

    def generate(self, **kwargs):
        meta = kwargs['metadata']
        if meta.get('role') != 'Prosecutor':
            return self.client.generate(**kwargs)
        if meta.get('stage') != 'indictment':
            raise ValueError('Unexpected Prosecutor replay stage')
        record = self.records.get(meta['sample_id'])
        model_input = json.loads(kwargs['user_prompt'])['input']
        if record is None or digest(model_input) != record['input_hash']:
            raise ValueError('Missing Prosecutor replay or input mismatch')
        value = deepcopy(record['report'])
        if kwargs.get('validator'):
            kwargs['validator'](value)
        if self.audit_path:
            append_jsonl(self.audit_path, {'sample_id': meta['sample_id'], 'input_hash': record['input_hash'],
                                         'report_hash': digest(value), 'snapshot_replay': True})
        return value


def stage_metrics(rows):
    result = {}
    counts = {'submitted_counts': Counter(), 'defender_counts': Counter(), 'final_counts': Counter()}
    for stage in ('prosecutor', 'submitted_defender', 'defender_policy', 'final'):
        scored = []
        for row in rows:
            p = row['prosecutor']['candidate_class']; de = row['defender']; gold = row['gold']
            direct = p if de['concede_charge'] else de['alternative_class']
            raw = row.get('defender_review')
            submitted = raw['alternative_assessment']['class'] if raw and raw['decision'] == 'challenge' else direct
            if submitted == 'None': submitted = p
            pred = {'prosecutor': p, 'submitted_defender': submitted,
                    'defender_policy': direct, 'final': row['prediction']}[stage]
            scored.append({**row, 'prediction': pred})
            key = {'submitted_defender':'submitted_counts', 'defender_policy':'defender_counts', 'final':'final_counts'}.get(stage)
            if key:
                c = counts[key]
                c['changed'] += pred != p
                c['beneficial'] += p != gold and pred == gold
                c['harmful'] += p == gold and pred != gold
                c['wrong_to_wrong'] += p != gold and pred != gold and pred != p
        result[stage] = score(scored)
    result.update({k:dict(v) for k,v in counts.items()})
    result['effective_decisions'] = dict(Counter(r.get('defender_validation', {}).get(
        'effective_decision', 'uphold' if r['defender']['concede_charge'] else 'challenge') for r in rows))
    result['gate_reasons'] = dict(Counter(reason for r in rows for reason in
        r.get('defender_validation', {}).get('gate_reasons', [])))
    result['arbiter_correct_alternative_rejected'] = sum(
        not r['defender']['concede_charge'] and r['defender']['alternative_class'] == r['gold']
        and r['prediction'] != r['gold'] for r in rows)
    result['counterfactual_note'] = 'submitted_defender and defender_policy accept proposals directly; not separate live pipelines'
    return result


def _samples(config):
    if config['task'] != 'classification' or config['engine']['adaptive_policy'] != 'adversarial':
        raise ValueError('Replay requires classification adversarial config')
    return {s.sample_id:s for s in select_task(load_split(Path(config['data_dir']) / (config['split']+'.json')), 'classification')}


def export_snapshot(config, predictions, output):
    from src.runner import validate_manifest
    if Path(output).exists(): raise ValueError('Snapshot output exists; choose a new path')
    path = Path(predictions)
    manifest = json.loads((path.parent / 'manifest.json').read_text())
    validate_manifest(manifest)
    source = manifest['experiment']
    if source['config']['task'] != 'classification' or manifest['split'] != config['split'] or source['config']['context'] != config['context']:
        raise ValueError('Source run task/split/context mismatch')
    datahash = file_hash(Path(config['data_dir']) / (config['split']+'.json'))
    if source['dataset_hashes'].get(config['split']) != datahash:
        raise ValueError('Source run dataset mismatch')
    rows = read_jsonl(path)
    ids = [r['sample_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(manifest['selection']['sample_ids']):
        raise ValueError('Source run coverage mismatch')
    samples = _samples(config)
    records = []
    for row in rows:
        sid = row['sample_id']
        if (row.get('status') != 'ok' or row['run_fingerprint'] != manifest['run_fingerprint']
            or sid not in samples or row['gold'] != samples[sid].gold('classification')):
            raise ValueError('Source record invalid or incomplete')
        records.append((sid, samples[sid].model_input(config['context']), row['prosecutor']))
    snapshot = build_snapshot(records, dataset_hash=datahash, split=config['split'], context=config['context'])
    write_json(output, snapshot)
    return snapshot


def prepare(config, snapshot_path, limit=None):
    from src.runner import experiment_identity
    samples = _samples(config)
    snapshot = json.loads(Path(snapshot_path).read_text())
    ids = [r['sample_id'] for r in snapshot['records']]
    if any(sid not in samples for sid in ids): raise ValueError('Snapshot IDs outside dataset')
    validate_snapshot(snapshot, {sid:samples[sid].model_input(config['context']) for sid in ids},
        dataset_hash=file_hash(Path(config['data_dir'])/(config['split']+'.json')),
        split=config['split'], context=config['context'])
    if limit is not None and (type(limit) is not int or limit < 1): raise ValueError('limit must be positive')
    ids = ids[:limit] if limit else ids
    body = {'experiment': experiment_identity(config), 'snapshot': snapshot['fingerprint'], 'sample_ids': ids}
    return snapshot, [samples[sid] for sid in ids], {**body, 'fingerprint':digest(body)}


def run_experiment(config, snapshot_path, output, *, limit=None, resume=False, frozen=None, client=None):
    snapshot, samples, identity = prepare(config, snapshot_path, limit)
    if config['split'] == 'test' and not frozen:
        raise ValueError('Test replay requires --frozen created by evaluate_defender.py freeze')
    if frozen and json.loads(Path(frozen).read_text()) != identity:
        raise ValueError('Replay frozen manifest differs from source/config/snapshot/selection')
    directory = Path(output); manifest = directory/'manifest.json'
    if manifest.exists():
        if not resume or json.loads(manifest.read_text()) != identity:
            raise ValueError('Replay output exists or resume identity differs')
    elif directory.exists() and any(directory.iterdir()):
        raise ValueError('Replay output is nonempty without manifest')
    else: write_json(manifest, identity)
    recover_audit_tail(directory/'raw_calls.jsonl')
    model = ModelConfig(**config['model'])
    client = client or Client(model, Path(config['cache_dir'])/'responses.sqlite', directory/'raw_calls.jsonl')
    replay = ReplayClient(client, snapshot, directory/'prosecutor_replay.jsonl')
    engine = Engine(replay, task='classification', **config['engine'])
    rows = []
    for index, sample in enumerate(samples, 1):
        target = directory/'samples'/(digest(sample.sample_id)+'.json')
        previous = json.loads(target.read_text()) if target.exists() else None
        if previous and (previous.get('run_fingerprint') != identity['fingerprint'] or previous.get('gold') != sample.gold('classification')):
            raise ValueError('Stored replay trace differs from run')
        if previous and previous.get('status') == 'ok': rows.append(previous); continue
        row = {'sample_id':sample.sample_id, 'task':'classification', 'gold':sample.gold('classification'),
               'run_fingerprint':identity['fingerprint'], 'status':'ok'}
        try:
            row.update(engine.run(sample.model_input(config['context']),
                {'sample_id':sample.sample_id, 'dataset':snapshot['dataset_hash'], 'split':config['split'],
                 'experiment':identity['fingerprint']}))
        except Exception as exc:
            row.update(status='error', error=f'{type(exc).__name__}: {exc}')
        write_json(target, row); rows.append(row)
        print(f'[{index}/{len(samples)}] {sample.sample_id}: {row["status"]}', flush=True)
        if row['status'] == 'error': break
    predictions = directory/'predictions.jsonl'
    # Atomic export, including the error record; no partial run is scored.
    temporary = predictions.with_suffix('.tmp')
    temporary.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
    temporary.replace(predictions)
    complete = len(rows) == len(samples) and all(r['status']=='ok' for r in rows)
    from src.runner import _audit_usage
    usage = _audit_usage(directory, config['model'])
    summary = {'status':'complete' if complete else 'incomplete', 'count':len(rows),
               'expected_count':len(samples), 'snapshot':snapshot['fingerprint'],
               'synthetic':model.provider=='mock', **usage,
               'metrics':stage_metrics(rows) if complete else None}
    write_json(directory/'summary.json', summary)
    return summary
