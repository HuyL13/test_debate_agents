"""V3 contracts: exact source trace, explicit scope and locked-node relations."""
import copy
import heapq
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

RESOURCE = Path(__file__).with_name('atomic_resources')


def schema():
    return json.loads((RESOURCE / 'atomic_proposition_schema_v3.json').read_text(encoding='utf-8'))


def segment(raw):
    """Conservative punctuation segmentation; offsets count Python Unicode characters."""
    result, start = [], 0
    for match in re.finditer(r'[.!?]+(?=\s|$)', raw):
        prefix = raw[start:match.end()]
        if re.search(r'\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|e\.g|i\.e)\.$', prefix, re.I):
            continue
        a, b = start, match.end()
        while a < b and raw[a].isspace():
            a += 1
        if a < b:
            result.append({'id': f'S{len(result)+1}', 'text': raw[a:b], 'start': a, 'end': b})
        start = b
    a, b = start, len(raw)
    while a < b and raw[a].isspace():
        a += 1
    while b > a and raw[b-1].isspace():
        b -= 1
    if a < b:
        result.append({'id': f'S{len(result)+1}', 'text': raw[a:b], 'start': a, 'end': b})
    if not result:
        raise ValueError('Empty input')
    return result


def resolve_quotes(quotes, sentences):
    by_id = {s['id']: s['text'] for s in sentences}
    spans = []
    for quote in quotes:
        text = quote['text']
        if not text or quote['sentence_id'] not in by_id:
            raise ValueError('Missing source sentence or empty quote')
        matches = list(re.finditer(re.escape(text), by_id[quote['sentence_id']]))
        occurrence = quote['occurrence']
        if type(occurrence) is not int or not 1 <= occurrence <= len(matches):
            raise ValueError(f'Quote not found at supplied occurrence: {text!r}. Copy exactly from sentence {quote["sentence_id"]}: {by_id[quote["sentence_id"]]!r}')
        match = matches[occurrence-1]
        spans.append({'sentence_id': quote['sentence_id'], 'start': match.start(), 'end': match.end(), 'text': text})
    return spans


def wire_schema(stage):
    """The provider emits exact quotes, never counts offsets or edits source sentences."""
    contract = copy.deepcopy(schema())
    keys = ['propositions', 'entities', 'references'] if stage == 'nodes' else ['discourse_edges', 'argument_edges']
    contract['properties'] = {k: contract['properties'][k] for k in keys}
    contract['required'] = keys
    if stage == 'edges':
        for item in contract['properties'].values():
            edge = item['items']
            edge['properties']['additional_evidence'] = edge['properties'].pop('source_spans')
            edge['properties']['additional_evidence']['minItems'] = 0
            edge['properties'].pop('evidence_sentence_ids')
            edge['required'] = [k for k in edge['required'] if k not in ('source_spans', 'evidence_sentence_ids')] + ['additional_evidence']
    def rewrite(node):
        if isinstance(node, dict):
            if set(node.get('properties', {})) == {'sentence_id', 'start', 'end', 'text'}:
                node['properties'].pop('start')
                node['properties'].pop('end')
                node['properties']['occurrence'] = {'type': 'integer', 'minimum': 1}
                node['required'] = ['sentence_id', 'text', 'occurrence']
            for item in node.values():
                rewrite(item)
        elif isinstance(node, list):
            for item in node:
                rewrite(item)
    rewrite(contract)
    return contract


def materialize(payload, sentences):
    obj = copy.deepcopy(payload)
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'sentence_id', 'text', 'occurrence'}:
                return resolve_quotes([value], sentences)[0]
            return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v) for v in value]
        return value
    return visit(obj)


def materialize_edges(payload, graph):
    obj = materialize(payload, graph['sentences'])
    nodes = {p['id']: p for p in graph['propositions']}
    sentence_order = {s['id']: i for i, s in enumerate(graph['sentences'])}
    for kind in ['discourse_edges', 'argument_edges']:
        for edge in obj[kind]:
            endpoints = edge['source_ids'] + [edge['target_id']]
            if not all(pid in nodes for pid in endpoints):
                raise ValueError('Edge references a missing locked node')
            spans = [span for pid in endpoints for span in nodes[pid]['source_spans']]
            spans += edge.pop('additional_evidence') + edge['surface_markers'] + edge.get('connective_spans', [])
            unique = {(s['sentence_id'], s['start'], s['end'], s['text']): s for s in spans}
            edge['source_spans'] = sorted(unique.values(), key=lambda s: (sentence_order[s['sentence_id']], s['start'], s['end']))
            edge['evidence_sentence_ids'] = sorted({s['sentence_id'] for s in spans}, key=sentence_order.__getitem__)
    return obj


def validate_graph(obj, raw, *, stage='edges'):
    errors = [f'{e.json_path}: {e.message}' for e in Draft202012Validator(schema()).iter_errors(obj)]
    if errors:
        raise ValueError('; '.join(errors))
    sentences = {s['id']: s for s in obj['sentences']}
    if obj['sentences'] != segment(raw):
        raise ValueError('Sentences/offsets must equal deterministic source segmentation')
    nodes = {p['id']: p for p in obj['propositions']}
    entities = {e['id']: e for e in obj['entities']}
    if len(nodes) != len(obj['propositions']) or len(entities) != len(obj['entities']):
        raise ValueError('Duplicate node/entity IDs')
    def check_span(span):
        sentence = sentences.get(span['sentence_id'])
        if not sentence or not 0 <= span['start'] < span['end'] <= len(sentence['text']):
            raise ValueError('Invalid source span bounds or sentence ID')
        if sentence['text'][span['start']:span['end']] != span['text']:
            raise ValueError('Source span quote mismatch')
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'sentence_id', 'start', 'end', 'text'}:
                check_span(value)
            else:
                for v in value.values():
                    visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)
    visit(obj)
    groups = {}
    coverage = set()
    for p in nodes.values():
        sids = {s['sentence_id'] for s in p['source_spans']}
        if sids != set(p['source_sentence_ids']):
            raise ValueError('Node source sentence IDs must match spans')
        coverage.update(sids)
        source = ' '.join(s['text'] for s in p['source_spans'])
        if '?' in source and p['speech_act'] != 'QUESTION':
            raise ValueError(f"Node {p['id']}: question-bearing source span requires QUESTION speech act")
        types = {op['type'] for op in p['operators']}
        if re.search(r'\b(may|might|perhaps|probably|seems|appears)\b', source, re.I) and not types & {'EPISTEMIC_HEDGE', 'HYPOTHETICAL'}:
            raise ValueError(f"Node {p['id']}: source {source!r} requires EPISTEMIC_HEDGE or HYPOTHETICAL, not operators={p['operators']!r}")
        if re.search(r'\bshould\b', source, re.I) and 'DEONTIC' not in types:
            raise ValueError(f"Node {p['id']}: source {source!r} contains should; add DEONTIC on THIS node, even for a belief attributed to someone else")
        if p['speech_act'] == 'ASSERTION' and re.match(r'^(may|might|should|could|would|must|never|probably)\b', p['text'], re.I):
            raise ValueError('Predicate fragment lacks an explicit subject')
        for op in p['operators']:
            conditional = op['type'].startswith('CONDITIONAL_')
            if conditional != bool(op['scope_group']):
                raise ValueError('Only conditional operators have a nonempty scope_group')
            if conditional:
                groups.setdefault(op['scope_group'], set()).add(op['type'])
    if coverage != set(sentences):
        raise ValueError('Every source sentence requires at least one proposition')
    for sentence in sentences.values():
        relevant = [p for p in nodes.values() if sentence['id'] in p['source_sentence_ids']]
        if '?' in sentence['text'] and not any(p['speech_act'] == 'QUESTION' for p in relevant):
            raise ValueError('Source question requires a QUESTION proposition')
        if re.match(r'^if\b', sentence['text'], re.I) and not any(op['type'] == 'CONDITIONAL_ANTECEDENT' for p in relevant for op in p['operators']):
            raise ValueError('Leading if requires explicit conditional antecedent scope')
    for group, roles in groups.items():
        if roles != {'CONDITIONAL_ANTECEDENT', 'CONDITIONAL_CONSEQUENT'}:
            raise ValueError(f'Unpaired conditional scope group {group}')
    for ref in obj['references']:
        allowed = entities if ref['referent_type'] == 'ENTITY' else nodes
        if any(r not in allowed for r in ref['referent_ids']):
            raise ValueError('Reference points to missing/wrong type of referent')
    incoming, adj, seen = dict.fromkeys(nodes, 0), {p: set() for p in nodes}, set()
    for kind in ['discourse_edges', 'argument_edges']:
        for edge in obj[kind]:
            endpoints = set(edge['source_ids']) | {edge['target_id']}
            if not endpoints <= set(nodes) or edge['target_id'] in edge['source_ids']:
                raise ValueError('Edge has missing endpoint or self-loop')
            signature = (kind, tuple(sorted(edge['source_ids'])), edge['target_id'], edge['relation'])
            if signature in seen:
                raise ValueError('Duplicate edge')
            seen.add(signature)
            evidence = set(edge['evidence_sentence_ids'])
            spans = edge['source_spans']
            if evidence != {s['sentence_id'] for s in spans} or not evidence <= set(sentences):
                raise ValueError('Edge evidence IDs do not match source spans')
            for pid in endpoints:
                if not all(any(a['sentence_id'] == b['sentence_id'] and a['start'] <= b['start'] and b['end'] <= a['end']
                               for a in spans) for b in nodes[pid]['source_spans']):
                    raise ValueError('Edge evidence must include source and target proposition spans')
            for marker in edge['surface_markers'] + edge.get('connective_spans', []):
                if not any(s['sentence_id'] == marker['sentence_id'] and s['start'] <= marker['start'] and marker['end'] <= s['end'] for s in spans):
                    raise ValueError('Marker is outside edge evidence')
            if kind == 'discourse_edges':
                markers = edge['connective_spans']
                if edge['origin'] == 'EXPLICIT':
                    if not markers:
                        raise ValueError('EXPLICIT needs exact connective spans')
                    for marker in markers:
                        phrase = edge['connective']
                        sentence = sentences[marker['sentence_id']]['text']
                        if marker['text'].lower() != phrase or (marker['start'] and sentence[marker['start']-1].isalnum()) or (marker['end'] < len(sentence) and sentence[marker['end']].isalnum()):
                            raise ValueError('EXPLICIT connective is not a whole phrase')
                elif markers:
                    raise ValueError('INFERRED has no explicit connective spans')
            else:
                target = edge['target_id']
                for source in edge['source_ids']:
                    if target not in adj[source]:
                        adj[source].add(target)
                        incoming[target] += 1
    queue = [p for p in nodes if not incoming[p]]
    processed = 0
    while queue:
        pid = queue.pop()
        processed += 1
        for target in adj[pid]:
            incoming[target] -= 1
            if not incoming[target]:
                queue.append(target)
    if processed != len(nodes):
        raise ValueError('Cycle in SUPPORT dependency graph')


def linearize(obj):
    nodes = {p['id']: p for p in obj['propositions']}
    rank = {s['id']: i for i, s in enumerate(obj['sentences'])}
    def key(pid):
        return min((rank[s['sentence_id']], s['start']) for s in nodes[pid]['source_spans']) + (pid,)
    adj, degree = {p: set() for p in nodes}, dict.fromkeys(nodes, 0)
    for e in obj['argument_edges']:
        for source in e['source_ids']:
            if e['target_id'] not in adj[source]:
                adj[source].add(e['target_id'])
                degree[e['target_id']] += 1
    queue = [key(p) for p in nodes if not degree[p]]
    heapq.heapify(queue)
    order = []
    while queue:
        *_, pid = heapq.heappop(queue)
        order.append(pid)
        for target in sorted(adj[pid]):
            degree[target] -= 1
            if not degree[target]:
                heapq.heappush(queue, key(target))
    if len(order) != len(nodes):
        raise ValueError('Cycle in SUPPORT dependency graph')
    lines = ['ATOMIC_NODES:']
    for pid in order:
        p = nodes[pid]
        operators = ','.join(sorted(op['type'] + (':' + op['scope_group'] if op['scope_group'] else '') for op in p['operators']))
        lines.append(f"{pid} [{p['speech_act']}; {operators}] := {p['text']}")
    for kind, heading in [('argument_edges', 'SUPPORT_CHAIN'), ('discourse_edges', 'DISCOURSE_EDGES')]:
        lines += ['', heading + ':']
        for e in sorted(obj[kind], key=lambda e: (tuple(sorted(e['source_ids'])), e['target_id'], e['relation'], e.get('connective', ''), e.get('origin', ''))):
            sources = ','.join(sorted(e['source_ids']))
            rel = e['relation']
            if kind == 'discourse_edges':
                rel += f"[{e['origin']}: {e['connective']}]"
            lines.append(f"{{{sources}}} --{rel}--> {e['target_id']}")
    return '\n'.join(lines + ['', 'LINEAR_ORDER:', ' | '.join(order)]) + '\n'


def statistics(obj):
    return {'nodes': len(obj['propositions']), 'discourse_edges': len(obj['discourse_edges']),
        'support_edges': len(obj['argument_edges']), 'inferred_edges': sum(e['origin'] == 'INFERRED' for e in obj['discourse_edges']),
        'speech_acts': dict(Counter(p['speech_act'] for p in obj['propositions'])),
        'operators': dict(Counter(op['type'] for p in obj['propositions'] for op in p['operators']))}
