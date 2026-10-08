import argparse
import html
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import yaml

from src.discourse_classification.data import load_records, partition
from src.discourse_classification.graph import StanzaParser, build_graph
from src.discourse_classification.patterns import retrieve
from src.discourse_classification.pipeline import VERSION, classify
from src.evaluate import score
from src.io_utils import append_jsonl, digest, file_hash, read_jsonl, recover_audit_tail, write_json, write_jsonl
from src.labels import FALLACIES
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.runner import expand_env, load_dotenv_file


def coverage(rows):
    result = {}
    for label in FALLACIES:
        subset = [r for r in rows if r['gold'] == label]
        count = sum(label in {c['label'] for c in r.get('primary_candidates', r.get('candidates', []))} for r in subset)
        result[label] = {'support': len(subset), 'covered': count, 'recall': count/len(subset) if subset else None}
    return result


def render_report(folder, rows, summary):
    def esc(value):
        return html.escape(str(value))
    body = []
    for row in rows:
        correct = row.get('prediction') == row['gold']
        details = {'evidence': row.get('evidence', []), 'candidates': row.get('candidates', []),
                   'verification': row.get('verification', []), 'calls': row.get('calls')}
        if 'role_extraction_status' in row:
            details['role_extraction_status'] = row['role_extraction_status']
            details['template_prediction'] = row.get('template_prediction')
        if 'role_completion_focus' in row:
            details['role_completion_focus'] = row['role_completion_focus']
            details['role_completion_status'] = row.get('role_completion_status')
            if 'role_completion_error' in row:
                details['role_completion_error'] = row['role_completion_error']
        if 'role_arguments' in row:
            details['role_arguments'] = row['role_arguments']
        if 'graph' in row:
            details['graph'] = row['graph']
        body.append(f'<tr class="{"correct" if correct else "wrong"}"><td>{esc(row["sample_id"])}</td>'
            f'<td>{esc(row["gold"])}</td><td>{esc(row.get("prediction", ""))}</td>'
            f'<td>{esc(row.get("decision_mode", row["status"]))}</td>'
            f'<td><details><summary>{esc(row.get("reason", row.get("error", "Coverage only")))}</summary>'
            f'<p>{esc(row["comment"])}</p><pre>{esc(json.dumps(details, ensure_ascii=False, indent=2))}</pre>'
            '</details></td></tr>')
    text = ('<!doctype html><meta charset="utf-8"><title>Discourse classification</title>'
        '<style>body{font:15px system-ui;margin:24px;background:#fafafa;color:#222}table{border-collapse:collapse;width:100%}'
        'td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}pre{white-space:pre-wrap;max-width:850px}'
        '.wrong td:nth-child(3){color:#b42318}.correct td:nth-child(3){color:#067647}summary{cursor:pointer}</style>'
        '<h1>Discourse classification</h1><p>Click a reason to inspect text, evidence, candidates and verification.</p>'
        f'<details><summary>Metrics / coverage</summary><pre>{esc(json.dumps(summary, indent=2))}</pre></details>'
        '<table><thead><tr><th>ID</th><th>Gold</th><th>Prediction</th><th>Decision</th><th>Reason / inspect</th></tr></thead>'
        '<tbody>' + ''.join(body) + '</tbody></table>')
    (folder / 'report.html').write_text(text, encoding='utf-8')


def execute(config, *, output='discourse', limit=None, resume=False, client=None, parser=None, coverage_only=False):
    workers = config.get('workers', 1)
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError('workers must be an integer from 1 to 8')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be a positive integer')
    method = config.get('method', 'graph')
    if method not in ('graph', 'rules', 'direct') or config.get('parser', 'stanza') not in ('stanza', 'rules'):
        raise ValueError('Unknown method or parser')
    for name, default in [('max_pairs', 8), ('max_per_label', 3)]:
        value = config.get(name, default)
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    rows = load_records(config['input'], config.get('context', 'paper'))
    part = config.get('partition', 'all')
    if part not in ('all', 'design', 'validation'):
        raise ValueError('partition must be all/design/validation')
    if part != 'all':
        if config.get('split') != 'train':
            raise ValueError('Partition is available only with split=train')
        design, validation = partition(rows, config.get('validation_fraction', .2), config.get('seed', 42))
        rows = design if part == 'design' else validation
    # Exclude the entire evaluated article set before limiting rows, including held-out articles.
    demo_exclusions = {r['article_id'] for r in rows if r.get('article_id') is not None}
    if limit:
        rows = rows[:limit]
    if not rows:
        raise ValueError('No classification samples selected')
    root = Path(config.get('output_root', 'runs')).resolve()
    folder = (root / output).resolve()
    if root not in folder.parents:
        raise ValueError('Output must stay inside output_root')
    effective_model = expand_env(config.get('model', {})) if not coverage_only else {}
    manifest = {'version': VERSION, 'config': config, 'effective_model': effective_model,
                'input_sha256': file_hash(config['input']),
                'sample_ids': [r['sample_id'] for r in rows], 'coverage_only': coverage_only}
    # Only environment variable names are stored, never credential values.
    if any(k in config.get('model', {}) for k in ('api_key', 'token', 'password')):
        raise ValueError('Use api_key_env rather than credentials in config')
    manifest_path = folder / 'manifest.json'
    if folder.exists() and any(folder.iterdir()):
        if not resume:
            raise ValueError('Output exists; choose a fresh name or --resume')
        if not manifest_path.exists() or digest(json.loads(manifest_path.read_text(encoding='utf-8'))) != digest(manifest):
            raise ValueError('Resume config, input, selection or method changed')
    folder.mkdir(parents=True, exist_ok=True)
    write_json(manifest_path, manifest)
    result_path = folder / 'results.jsonl'
    if resume:
        recover_audit_tail(result_path)
    existing = list(read_jsonl(result_path)) if resume and result_path.exists() else []
    successful = {r['sample_id']: r for r in existing if r['status'] in ('ok', 'unresolved')}
    if len({r['sample_id'] for r in existing}) != len(existing):
        raise ValueError('Duplicate result IDs')
    # Retry failed items without keeping duplicate stale records.
    if existing:
        write_jsonl(result_path, successful.values())
    if parser is None and method == 'graph' and config.get('parser', 'stanza') == 'stanza':
        print('Loading Stanza parser...', flush=True)
        parser = StanzaParser(config.get('model_dir', 'cache/stanza'))
    if client is None and not coverage_only:
        client = Client(ModelConfig(**effective_model), folder / 'cache.sqlite3',
                        os.devnull, raw_debug_path=None)
    if parser is not None and workers > 1:
        original_parser, parser_lock = parser, Lock()
        def locked_parser(text):
            with parser_lock:
                return original_parser(text)
        parser = locked_parser
    completed = [successful[r['sample_id']] for r in rows if r['sample_id'] in successful]
    print(f'{method}: {len(rows)} samples -> {folder}', flush=True)
    def process(i, row):
        sid = row['sample_id']
        stage_state = {'stage': 'parsing'}
        def progress(stage):
            stage_state['stage'] = stage
            if len(rows) <= 10:
                print(f'[{i}/{len(rows)}] {sid}: {stage}', flush=True)
        try:
            sources = {k: row[k] for k in ('comment', 'title', 'parent_comment', 'article') if k in row}
            if coverage_only:
                graph = build_graph(row['comment'], parser)
                result = {'candidates': retrieve(graph, config.get('max_per_label', 3)), 'graph': graph,
                          'decision_mode': 'coverage', 'prediction': None}
            else:
                result = classify(client, sources, sid, parser=parser, method=method,
                    implicit=config.get('implicit', True), max_pairs=config.get('max_pairs', 8),
                    max_per_label=config.get('max_per_label', 3),
                    progress=progress, engine=config.get('engine', 'roles'), recovery=config.get('recovery', False),
                    use_relations=config.get('use_relations', True), demo_exclusions=demo_exclusions)
                result['prediction'] = result.pop('label')
            record = {'sample_id': sid, 'task': 'classification', 'gold': row['gold'],
                      'comment': row['comment'], 'status': 'unresolved' if result.get('decision_mode') == 'unresolved' else 'ok', **result}
        except (ValueError, RuntimeError, OSError) as exc:
            detail = str(exc)
            secret = os.environ.get(config.get('model', {}).get('api_key_env', ''))
            if secret:
                detail = detail.replace(secret, '[redacted]')
            record = {'sample_id': sid, 'task': 'classification', 'gold': row['gold'],
                      'comment': row['comment'], 'status': 'error', 'error_stage': stage_state['stage'],
                      'error': type(exc).__name__ + ': ' + detail[:240],
                      **getattr(exc, 'discourse_trace', {})}
        return i, record

    pending = [(i, row) for i, row in enumerate(rows, 1) if row['sample_id'] not in successful]
    def records():
        if workers == 1:
            for i, row in pending:
                yield process(i, row)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(process, i, row) for i, row in pending]
                for future in as_completed(futures):
                    yield future.result()

    for i, record in records():
        if record['status'] == 'error':
            print(f'[{i}/{len(rows)}] {record["sample_id"]}: ERROR at {record["error_stage"]}; see report, rerun with --resume', flush=True)
        append_jsonl(result_path, record)
        completed.append(record)
        if len(completed) % 10 == 0 or len(completed) == len(rows):
            print(f'Progress {len(completed)}/{len(rows)}; errors={sum(r["status"] == "error" for r in completed)}', flush=True)
            summary = summarize(completed, coverage_only, method)
            write_json(folder / 'metrics.json', summary)
            render_report(folder, completed, summary)
    positions = {row['sample_id']: i for i, row in enumerate(rows)}
    completed.sort(key=lambda r: positions[r['sample_id']])
    write_jsonl(result_path, completed)
    summary = summarize(completed, coverage_only, method)
    write_json(folder / 'metrics.json', summary)
    render_report(folder, completed, summary)
    print(f'Done: ok={summary["ok"]}, unresolved={summary["unresolved"]}, errors={summary["errors"]}, recovery={summary["recovery_count"]}; report.html', flush=True)
    return summary


def summarize(rows, coverage_only, method):
    accepted = [r for r in rows if r['status'] == 'ok']
    summary = {'selected': len(rows), 'ok': len(accepted), 'errors': sum(r['status'] == 'error' for r in rows),
               'unresolved': sum(r['status'] == 'unresolved' for r in rows),
               'role_completion_failures': sum(r.get('role_completion_status') == 'failed' for r in rows),
               'role_extraction_failures': sum(r.get('role_extraction_status') == 'failed' for r in rows),
               'coverage': coverage(rows) if method != 'direct' else None,
               'coverage_note': 'Rule anchors only; excludes role extraction.' if coverage_only else
                   'Primary candidates across all selected samples; unavailable traces count as uncovered.',
               'recovery_count': sum(r.get('decision_mode', '').startswith('recovery') for r in accepted),
               'decision_modes': dict(Counter(r.get('decision_mode') for r in accepted))}
    if not coverage_only:
        summary['completion_rate'] = len(accepted)/len(rows) if rows else 0
        summary['accuracy_all_selected'] = sum(r.get('prediction') == r['gold'] for r in accepted)/len(rows) if rows else 0
        primary = [r for r in rows if r.get('primary_prediction') is not None]
        summary['primary_decisions'] = len(primary)
        summary['primary_correct'] = sum(r['primary_prediction'] == r['gold'] for r in primary)
    if accepted and not coverage_only:
        summary.update(score(accepted))
        summary['metrics_scope'] = 'resolved samples only' if len(accepted) < len(rows) else 'all selected samples'
        summary['recovery_rate'] = summary['recovery_count']/len(accepted)
    return summary


def cli():
    ap = argparse.ArgumentParser(description='Eight-label code-first graph classification; compact inspectable results.')
    ap.add_argument('--config', default='configs/discourse_classification.yaml')
    ap.add_argument('--input', help='Classification JSON or upstream article JSON; overrides config input')
    ap.add_argument('--split', choices=['train', 'dev', 'test'])
    ap.add_argument('--partition', choices=['all', 'design', 'validation'])
    ap.add_argument('--method', choices=['graph', 'rules', 'direct'])
    ap.add_argument('--output', default='discourse')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, help='Concurrent samples, 1-8; parser remains serialized')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--coverage-only', action='store_true')
    ap.add_argument('--without-relations', action='store_true', help='Ablation: preserve spans, omit graph relations')
    ap.add_argument('--download-models', action='store_true')
    args = ap.parse_args()
    base = Path(args.config).resolve().parent.parent
    load_dotenv_file(base / '.env')
    config = yaml.safe_load(Path(args.config).read_text(encoding='utf-8'))
    if args.split:
        config['split'] = args.split
        config['input'] = f'data/cocolofa/{args.split}.json'
    for key in ('input', 'partition', 'method'):
        value = getattr(args, key)
        if value:
            config[key] = value
    if args.without_relations:
        config['use_relations'] = False
    if args.workers is not None:
        config['workers'] = args.workers
    for key in ('input', 'model_dir', 'output_root'):
        value = Path(config[key])
        config[key] = str(value if value.is_absolute() else base / value)
    if args.download_models:
        import stanza
        stanza.download('en', model_dir=config['model_dir'],
            processors='tokenize,pos,lemma,depparse,constituency', verbose=False)
        print('Stanza models ready.', flush=True)
        return 0
    report = execute(config, output=args.output, limit=args.limit, resume=args.resume, coverage_only=args.coverage_only)
    return 1 if report['errors'] else 0
