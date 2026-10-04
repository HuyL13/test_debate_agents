#!/usr/bin/env python3
"""Validate atomic proposition JSON v2.0: schema + ID integrity + support DAG.
Usage: python validate_atomic_graph.py input.json [schema.json]
Semantic correctness of implicit relations still requires source-grounded review.
"""
import json
import sys
from pathlib import Path
from collections import deque
from jsonschema import Draft202012Validator

DEFAULT_SCHEMA = Path(__file__).with_name('atomic_proposition_schema_v2.json')


def check_graph(obj, schema):
    errors = [f'SCHEMA {e.json_path}: {e.message}' for e in Draft202012Validator(schema).iter_errors(obj)]
    if errors:
        return errors
    sentence_by_id = {s['id']: s for s in obj['sentences']}
    proposition_by_id = {p['id']: p for p in obj['propositions']}
    if len(sentence_by_id) != len(obj['sentences']):
        errors.append('Duplicate sentence ID')
    if len(proposition_by_id) != len(obj['propositions']):
        errors.append('Duplicate proposition ID')
    for p in obj['propositions']:
        for sid in p['source_sentence_ids']:
            if sid not in sentence_by_id:
                errors.append(f'Node {p["id"]}: missing sentence {sid}')
    for ref in obj['references']:
        if ref['sentence_id'] not in sentence_by_id:
            errors.append(f'Reference: missing sentence {ref["sentence_id"]}')
        for pid in ref['referent_proposition_ids']:
            if pid not in proposition_by_id:
                errors.append(f'Reference: missing proposition {pid}')
    seen=set()
    for kind in ['discourse_edges', 'argument_edges']:
        for e in obj[kind]:
            sig=(kind,tuple(sorted(e['source_ids'])),e['target_id'],e['relation'])
            if sig in seen:
                errors.append(f'Duplicate edge {sig}')
            seen.add(sig)
            for src in e['source_ids']:
                if src not in proposition_by_id:
                    errors.append(f'Edge: missing source {src}')
                if src == e['target_id']:
                    errors.append(f'Edge: self-loop {src}')
            if e['target_id'] not in proposition_by_id:
                errors.append(f'Edge: missing target {e["target_id"]}')
            for sid in e['evidence_sentence_ids']:
                if sid not in sentence_by_id:
                    errors.append(f'Edge: missing evidence sentence {sid}')
            if kind=='discourse_edges' and e['origin']=='EXPLICIT':
                phrase=e['connective'].lower()
                if not any(phrase in sentence_by_id[sid]['text'].lower() for sid in e['evidence_sentence_ids'] if sid in sentence_by_id):
                    errors.append(f'EXPLICIT connective not found in evidence: {phrase}')
    # SUPPORT dependency DAG: a hyperedge is modeled as each source preceding target.
    nodes=set(proposition_by_id)
    incoming={n:0 for n in nodes}
    adj={n:set() for n in nodes}
    for edge in obj['argument_edges']:
        t=edge['target_id']
        for s in edge['source_ids']:
            if s in nodes and t in nodes and s!=t and t not in adj[s]:
                adj[s].add(t)
                incoming[t]+=1
    queue=deque(sorted([n for n in nodes if incoming[n]==0]))
    processed=0
    while queue:
        node=queue.popleft();processed+=1
        for tgt in sorted(adj[node]):
            incoming[tgt]-=1
            if incoming[tgt]==0:
                queue.append(tgt)
    if processed!=len(nodes):
        errors.append('Cycle in SUPPORT dependency graph')
    return errors


def main():
    if len(sys.argv) not in (2,3):
        print(__doc__.strip());sys.exit(2)
    graph=json.loads(Path(sys.argv[1]).read_text())
    schema=json.loads(Path(sys.argv[2] if len(sys.argv)==3 else DEFAULT_SCHEMA).read_text())
    errors=check_graph(graph,schema)
    if errors:
        print('INVALID',len(errors),'errors')
        for error in errors: print('-',error)
        sys.exit(1)
    print('VALID: schema, identifiers, edge vocabulary, explicit connective presence, SUPPORT DAG')
    print('NOTE: Semantics still require grounded interpretation; form validation cannot prove entailment.')

if __name__=='__main__':
    main()
