"""Bounded extraction/review/repair; semantic issues never become graph edges."""
import json
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.atomic_graph import select_samples
from src.atomic_v3 import segment, wire_schema, materialize, materialize_edges, validate_graph, linearize, statistics
from src.atomic_resources.prompts_v3 import NODES, EDGES, REVIEW, VERSION
from src.data.loader import load_split
from src.io_utils import write_json, write_jsonl
from src.llm.client import Client
from src.llm.config import ModelConfig

ISSUE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['issues'], 'properties': {
    'issues': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'required': ['node_ids', 'edge_ids', 'rule', 'source_quote', 'explanation', 'proposed_action'],
        'properties': {'node_ids': {'type': 'array', 'items': {'type': 'string'}},
            'edge_ids': {'type': 'array', 'items': {'type': 'string'}},
            'rule': {'type': 'string', 'minLength': 1}, 'source_quote': {'type': 'string', 'minLength': 1},
            'explanation': {'type': 'string', 'minLength': 1},
            'proposed_action': {'enum': ['RETRY_EXTRACTION', 'RETRY_RELATION', 'NEEDS_HUMAN_REVIEW', 'PASS']}}}}}}


class ExtractionError(ValueError):
    def __init__(self, message, issues, trace):
        super().__init__(message)
        self.issues, self.trace = issues, trace


def extract(client, raw, sample_id, *, semantic_review=True, max_repairs=1):
    sentences = segment(raw)
    graph = {'schema_version': '3.0', 'document_id': sample_id, 'sentences': sentences,
             'propositions': [], 'entities': [], 'references': [], 'discourse_edges': [], 'argument_edges': []}
    issues, trace = [], []
    def call(stage, system, payload, contract, validator):
        paths = {name: getattr(client, attr, None) for name, attr in [('attempts', 'audit_path'), ('responses', 'raw_debug_path')]}
        positions = {name: Path(path).stat().st_size if path and Path(path).exists() else 0 for name, path in paths.items()}
        record = {'stage': stage, 'input': payload, 'output': None, 'stats': None}
        try:
            result = client.generate(system_prompt=system, user_prompt=json.dumps(payload, ensure_ascii=False),
                schema=contract, metadata={'stage': 'atomic_v3_' + stage, 'sample_id': sample_id, 'prompt_version': VERSION},
                validator=validator)
            record.update({'output': result.output, 'stats': asdict(result.stats) if result.stats is not None else None})
        except (ValueError, RuntimeError, OSError) as exc:
            record['error'] = str(exc)
            raise
        finally:
            for name, path in paths.items():
                record[name] = []
                if path and Path(path).exists():
                    with Path(path).open('rb') as stream:
                        stream.seek(positions[name])
                        record[name] = [json.loads(line) for line in stream.read().decode('utf-8').splitlines() if line.strip()]
            trace.append(record)
        return result.output
    try:
        for stage, system in [('nodes', NODES), ('edges', EDGES)]:
            feedback = []
            accepted = False
            for attempt in range(max_repairs + 1):
                payload = {'target': raw, 'sentences': sentences, 'repair_feedback': feedback}
                if stage == 'edges':
                    payload['locked'] = {k: graph[k] for k in ['propositions', 'entities', 'references']}
                def convert(output):
                    return materialize(output, sentences) if stage == 'nodes' else materialize_edges(output, graph)
                def validate_wire(output):
                    merged = {**graph, **convert(output)}
                    validate_graph(merged, raw, stage=stage)
                output = call(stage, system, payload, wire_schema(stage), validate_wire)
                draft = {**graph, **convert(output)}
                if not semantic_review:
                    graph = draft
                    accepted = True
                    break
                def validate_review(review):
                    nodes = {p['id'] for p in draft['propositions']}
                    edge_ids = {f'D{i+1}' for i in range(len(draft['discourse_edges']))} | {f'A{i+1}' for i in range(len(draft['argument_edges']))}
                    for issue in review['issues']:
                        if issue['source_quote'] not in raw:
                            raise ValueError('Reviewer source_quote must be an exact substring of the raw target')
                        if not set(issue['node_ids']) <= nodes or not set(issue['edge_ids']) <= edge_ids:
                            raise ValueError('Reviewer issue IDs must exist in the reviewed extraction')
                reviewed = {k: v for k, v in draft.items() if k not in ('document_id', 'schema_version')}
                review = call('review_' + stage, REVIEW,
                    {'target': raw, 'stage': stage, 'extraction': reviewed}, ISSUE_SCHEMA, validate_review)
                current = [{**issue, 'sample_id': sample_id, 'stage': stage, 'attempt': attempt + 1} for issue in review['issues']]
                issues.extend(current)
                blocking = [issue for issue in current if issue['proposed_action'] != 'PASS']
                if not blocking:
                    graph = draft
                    accepted = True
                    break
                feedback = [{k: v for k, v in issue.items() if k not in ('sample_id', 'stage', 'attempt')} for issue in blocking]
                if any(i['proposed_action'] == 'NEEDS_HUMAN_REVIEW' or (stage == 'edges' and i['proposed_action'] == 'RETRY_EXTRACTION') for i in blocking):
                    break
            if not accepted:
                raise ValueError(f'{stage}: unresolved semantic issues after bounded repair; needs human review')
        validate_graph(graph, raw)
        return graph, issues, trace
    except (ValueError, RuntimeError, OSError) as exc:
        raise ExtractionError(str(exc), issues, trace) from exc


def execute(config, output, *, limit=10, seed=42, client=None):
    output = Path(output)
    selected = select_samples(load_split(Path(config['data_dir']) / f"{config['split']}.json"), limit, seed)
    inputs = [{'sample_id': s.sample_id, 'comment': s.comment} for s in selected]
    if output.exists() and any(output.iterdir()):
        raise ValueError('V3 requires a fresh output directory to preserve previous results')
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'inputs.json', inputs)
    write_json(output / 'config_snapshot.json', config)
    (output / 'prompt_version.txt').write_text(VERSION + '\n', encoding='utf-8')
    client = client or Client(ModelConfig(**config['model']), output / 'cache.sqlite3', output / 'api_calls.jsonl', raw_debug_path=output / 'raw_calls.jsonl')
    review_enabled = config.get('semantic_review', True)
    repairs = config.get('max_semantic_repairs', 1)
    if type(review_enabled) is not bool or type(repairs) is not int or not 0 <= repairs <= 3:
        raise ValueError('semantic_review must be boolean and max_semantic_repairs must be 0..3')
    report = {'schema_version': '3.0', 'prompt_version': VERSION, 'split': config['split'], 'seed': seed,
        'requested': limit, 'valid': 0, 'failed': 0, 'semantic_review_enabled': review_enabled, 'samples': [],
        'note': 'valid means structure passed and configured reviewer accepted; this is not semantic gold accuracy.'}
    reviews = []
    for sample in selected:
        print(f'V3 extracting/reviewing {sample.sample_id}', flush=True)
        started = time.monotonic()
        try:
            graph, issues, trace = extract(client, sample.comment, sample.sample_id,
                semantic_review=review_enabled, max_repairs=repairs)
            stem = sample.sample_id.replace(':', '__')
            write_json(output / 'graphs' / f'{stem}.json', graph)
            folder = output / 'linearized'
            folder.mkdir(exist_ok=True)
            (folder / f'{stem}.txt').write_text(linearize(graph), encoding='utf-8')
            row = {'sample_id': sample.sample_id, 'valid': True, **statistics(graph)}
            report['valid'] += 1
        except ExtractionError as exc:
            issues, trace = exc.issues, exc.trace
            row = {'sample_id': sample.sample_id, 'valid': False, 'error': str(exc)}
            report['failed'] += 1
        reviews.extend(issues)
        row.update({'latency_seconds': time.monotonic() - started, 'semantic_issues': len(issues),
            'issue_rules': dict(Counter(i['rule'] for i in issues)),
            'provider_calls': sum(sum(not a.get('cache_hit', False) for a in t['attempts']) if t['attempts'] else (t['stats'] or {}).get('provider_calls', 0) for t in trace),
            'tokens': sum(sum((r.get('response', {}).get('usage') or {}).get('total_tokens', 0) for r in t['responses']) for t in trace)})
        report['samples'].append(row)
        write_json(output / 'traces' / f"{sample.sample_id.replace(':', '__')}.json", trace)
        write_jsonl(output / 'semantic_review.jsonl', reviews)
        write_json(output / 'report.json', report)
    return report


def apply_manual_review(output, issues):
    """Source-grounded human QA can override a false-negative automatic review.

    Retain blocked graphs/linearizations as drafts, outside accepted output.
    This never modifies node/edge content or turns review observations into edges.
    """
    output = Path(output).resolve()
    report_path = output / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    inputs = {s['sample_id']: s['comment'] for s in json.loads((output / 'inputs.json').read_text(encoding='utf-8'))}
    rows = {s['sample_id']: s for s in report['samples']}
    for issue in issues:
        sid = issue['sample_id']
        if sid not in rows or not issue['source_quote'] or issue['source_quote'] not in inputs[sid]:
            raise ValueError('Manual review needs a known sample and verbatim source quote')
        if issue['proposed_action'] not in ('PASS', 'NEEDS_HUMAN_REVIEW'):
            raise ValueError('Manual review records PASS or NEEDS_HUMAN_REVIEW')
        stem = sid.replace(':', '__')
        if '/' in stem or '\\' in stem or stem in ('.', '..'):
            raise ValueError('Unsafe sample filename')
    report.setdefault('automatic_valid', report['valid'])
    for issue in issues:
        row = rows[issue['sample_id']]
        if row.get('manual_review') != 'NEEDS_HUMAN_REVIEW':
            row['manual_review'] = issue['proposed_action']
        if issue['proposed_action'] == 'PASS' or not row['valid']:
            continue
        row['automatic_review_accepted'] = True
        row['valid'] = False
        row['error'] = 'Manual semantic review: ' + issue['explanation']
        stem = issue['sample_id'].replace(':', '__')
        for folder, suffix in [('graphs', '.json'), ('linearized', '.txt')]:
            source = output / folder / (stem + suffix)
            destination = output / 'drafts' / folder / (stem + suffix)
            if source.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ValueError('A preserved manual-review draft already exists')
                source.rename(destination)
    report['valid'] = sum(r['valid'] for r in rows.values())
    report['failed'] = len(rows) - report['valid']
    report['manual_review_completed'] = True
    report['note'] = 'Final valid excludes manual semantic issues; review judgments are not gold performance accuracy.'
    write_json(output / 'manual_review.json', issues)
    log_path = output / 'semantic_review.jsonl'
    existing = [json.loads(line) for line in log_path.read_text(encoding='utf-8').splitlines() if line.strip()] if log_path.exists() else []
    write_jsonl(log_path, existing + [{**i, 'reviewer': 'human'} for i in issues])
    write_json(report_path, report)
    return report
