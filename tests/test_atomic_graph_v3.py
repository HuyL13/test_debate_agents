from copy import deepcopy

import pytest

from src.atomic_v3 import segment, resolve_quotes, validate_graph, linearize


def fixture():
    raw = 'If the rule changes, will people object?'
    sentences = segment(raw)
    return raw, {
        'schema_version': '3.0', 'document_id': 'demo', 'sentences': sentences,
        'propositions': [
            {'id': 'P01', 'text': 'The rule changes.', 'source_sentence_ids': ['S1'],
             'source_spans': [{'sentence_id': 'S1', 'start': 3, 'end': 19, 'text': 'the rule changes'}],
             'speech_act': 'ASSERTION', 'operators': [{'type': 'CONDITIONAL_ANTECEDENT', 'scope_group': 'C1'}],
             'normalization_note': ''},
            {'id': 'P02', 'text': 'Will people object?', 'source_sentence_ids': ['S1'],
             'source_spans': [{'sentence_id': 'S1', 'start': 21, 'end': 40, 'text': 'will people object?'}],
             'speech_act': 'QUESTION', 'operators': [{'type': 'CONDITIONAL_CONSEQUENT', 'scope_group': 'C1'}],
             'normalization_note': ''}],
        'entities': [], 'references': [], 'discourse_edges': [], 'argument_edges': []}


def test_segmentation_and_quotes_preserve_unicode_and_repetition():
    raw = 'Dr. An says café. Women? Women?'
    sentences = segment(raw)
    assert len(sentences) == 3
    assert all(raw[s['start']:s['end']] == s['text'] for s in sentences)
    spans = resolve_quotes([{'sentence_id': 'S1', 'text': 'café', 'occurrence': 1}], sentences)
    assert spans[0]['text'] == 'café'
    with pytest.raises(ValueError):
        resolve_quotes([{'sentence_id': 'S1', 'text': 'invented', 'occurrence': 1}], sentences)


def test_conditional_question_is_preserved_and_linearization_stable():
    raw, obj = fixture()
    validate_graph(obj, raw)
    assert 'QUESTION' in linearize(obj)
    assert 'CONDITIONAL_ANTECEDENT:C1' in linearize(obj)
    changed = deepcopy(obj)
    changed['propositions'].reverse()
    assert linearize(changed) == linearize(obj)


@pytest.mark.parametrize('bad', ['span', 'scope', 'reference', 'question', 'candidate', 'cycle'])
def test_rejects_invalid_provenance_and_closed_contract(bad):
    raw, obj = fixture()
    if bad == 'span':
        obj['propositions'][0]['source_spans'][0]['end'] = 18
    elif bad == 'scope':
        obj['propositions'][1]['operators'] = []
    elif bad == 'reference':
        obj['references'] = [{'mention': obj['propositions'][0]['source_spans'][0],
            'referent_type': 'ENTITY', 'referent_ids': ['E99'], 'evidence_spans': [obj['propositions'][0]['source_spans'][0]]}]
    elif bad == 'question':
        obj['propositions'][1]['speech_act'] = 'ASSERTION'
    elif bad == 'candidate':
        obj['candidate_edges'] = []
    else:
        for source, target in [('P01', 'P02'), ('P02', 'P01')]:
            obj['argument_edges'].append({'source_ids': [source], 'target_id': target, 'relation': 'SUPPORT',
                'evidence_sentence_ids': ['S1'], 'source_spans': [p['source_spans'][0] for p in obj['propositions']],
                'surface_markers': [], 'justification': 'The author uses the premise as a reason.'})
    with pytest.raises(ValueError):
        validate_graph(obj, raw)


def test_joint_and_independent_support_and_no_discourse_dependency():
    raw, obj = fixture()
    edge = {'source_ids': ['P01'], 'target_id': 'P02', 'relation': 'SUPPORT',
        'evidence_sentence_ids': ['S1'], 'source_spans': [p['source_spans'][0] for p in obj['propositions']],
        'surface_markers': [], 'justification': 'Reason offered by the author.'}
    obj['argument_edges'] = [edge]
    validate_graph(obj, raw)
    assert '{P01} --SUPPORT--> P02' in linearize(obj)


def test_joint_and_independent_reasons_remain_distinct_groups():
    raw = 'Residents object. Roads close. Cancel the event.'
    sentences = segment(raw)
    nodes = [{'id': f'P{i+1:02}', 'text': s['text'], 'source_sentence_ids': [s['id']],
        'source_spans': resolve_quotes([{'sentence_id': s['id'], 'text': s['text'], 'occurrence': 1}], sentences),
        'speech_act': 'DIRECTIVE' if i == 2 else 'ASSERTION', 'operators': [], 'normalization_note': ''}
        for i, s in enumerate(sentences)]
    obj = {'schema_version': '3.0', 'document_id': 'demo', 'sentences': sentences, 'propositions': nodes,
        'entities': [], 'references': [], 'discourse_edges': [], 'argument_edges': []}
    def edge(sources):
        endpoints = [nodes[int(pid[1:])-1] for pid in sources + ['P03']]
        return {'source_ids': sources, 'target_id': 'P03', 'relation': 'SUPPORT',
            'source_spans': [p['source_spans'][0] for p in endpoints],
            'evidence_sentence_ids': [p['source_sentence_ids'][0] for p in endpoints],
            'surface_markers': [], 'justification': 'The author offers these reasons for cancellation.'}
    obj['argument_edges'] = [edge(['P01', 'P02'])]
    validate_graph(obj, raw)
    assert '{P01,P02} --SUPPORT--> P03' in linearize(obj)
    obj['argument_edges'] = [edge(['P01']), edge(['P02'])]
    validate_graph(obj, raw)
    text = linearize(obj)
    assert '{P01} --SUPPORT--> P03' in text and '{P02} --SUPPORT--> P03' in text
    assert '{P01,P02}' not in text


def test_entity_reference_and_explicit_connective_contract():
    raw, obj = fixture()
    mention = resolve_quotes([{'sentence_id': 'S1', 'text': 'people', 'occurrence': 1}], obj['sentences'])[0]
    obj['entities'] = [{'id': 'E01', 'text': 'people', 'source_spans': [mention]}]
    obj['references'] = [{'mention': mention, 'referent_type': 'ENTITY', 'referent_ids': ['E01'], 'evidence_spans': [mention]}]
    full = resolve_quotes([{'sentence_id': 'S1', 'text': raw, 'occurrence': 1}], obj['sentences'])
    marker = resolve_quotes([{'sentence_id': 'S1', 'text': 'If', 'occurrence': 1}], obj['sentences'])
    obj['discourse_edges'] = [{'source_ids': ['P01'], 'target_id': 'P02', 'relation': 'CONDITION', 'connective': 'if',
        'origin': 'EXPLICIT', 'connective_spans': marker, 'source_spans': full, 'evidence_sentence_ids': ['S1'],
        'surface_markers': marker, 'justification': 'Explicit conditional relation.'}]
    validate_graph(obj, raw)
    assert '--CONDITION[EXPLICIT: if]-->' in linearize(obj)
    assert obj['argument_edges'] == []
    obj['discourse_edges'][0]['relation'] = 'CAUSAL'
    with pytest.raises(ValueError):
        validate_graph(obj, raw)


def test_runner_repairs_nodes_before_locking_and_does_not_expose_sample_id(tmp_path):
    from types import SimpleNamespace
    import json
    from src.atomic_v3_runner import extract

    calls = []
    class Client:
        def generate(self, **kwargs):
            payload = json.loads(kwargs['user_prompt'])
            assert 'sample_id' not in payload and 'document_id' not in payload
            calls.append(kwargs['metadata']['stage'])
            stage = calls[-1]
            if stage == 'atomic_v3_nodes':
                output = {'propositions': [{'id': 'P01', 'text': 'Residents might object.',
                    'source_sentence_ids': ['S1'], 'source_spans': [{'sentence_id': 'S1', 'text': 'Residents might object.', 'occurrence': 1}],
                    'speech_act': 'ASSERTION', 'operators': [{'type': 'EPISTEMIC_HEDGE', 'scope_group': ''}], 'normalization_note': ''}],
                    'entities': [], 'references': []}
            elif stage == 'atomic_v3_edges':
                assert payload['locked']['propositions'][0]['operators'][0]['type'] == 'EPISTEMIC_HEDGE'
                output = {'discourse_edges': [], 'argument_edges': []}
            else:
                output = {'issues': []}
                if calls.count('atomic_v3_review_nodes') == 1 and stage == 'atomic_v3_review_nodes':
                    output['issues'] = [{'node_ids': ['P01'], 'edge_ids': [], 'rule': 'scope',
                        'source_quote': 'might', 'explanation': 'Check hedge scope.', 'proposed_action': 'RETRY_EXTRACTION'}]
            kwargs.get('validator', lambda x: None)(output)
            return SimpleNamespace(output=output, stats=None)

    obj, issues, trace = extract(Client(), 'Residents might object.', 'sample-secret', semantic_review=True, max_repairs=1)
    assert obj['document_id'] == 'sample-secret'
    assert calls.count('atomic_v3_nodes') == 2
    assert calls[-1] == 'atomic_v3_review_edges'
    assert len(issues) == 1
    assert len(trace) == 6


@pytest.mark.parametrize('text,operators,speech_act', [
    ('Waving off concerns may harm freedom.', [], 'ASSERTION'),
    ('The battle should never be disparaged.', [], 'ASSERTION'),
    ('It appears the government allowed violence.', [], 'ASSERTION'),
    ('Who would not find that exciting?', [], 'ASSERTION'),
    ('If the court must act, so be it.', [], 'ASSERTION'),
    ('Perhaps the government knows best.', [], 'ASSERTION'),
    ('This system probably never will work well.', [], 'ASSERTION'),
    ('Youth might leave.', [], 'ASSERTION'),
])
def test_scope_regressions_reject_unmarked_source(text, operators, speech_act):
    sentences = segment(text)
    obj = {'schema_version': '3.0', 'document_id': 'demo', 'sentences': sentences,
        'propositions': [{'id': 'P01', 'text': text, 'source_sentence_ids': ['S1'],
            'source_spans': resolve_quotes([{'sentence_id': 'S1', 'text': text, 'occurrence': 1}], sentences),
            'speech_act': speech_act, 'operators': operators, 'normalization_note': ''}],
        'entities': [], 'references': [], 'discourse_edges': [], 'argument_edges': []}
    with pytest.raises(ValueError):
        validate_graph(obj, text)


@pytest.mark.parametrize('stage', ['atomic_v3_nodes', 'atomic_v3_edges', 'atomic_v3_review_nodes', 'atomic_v3_review_edges'])
def test_v3_truncation_retry_requires_full_stage_json(stage):
    from src.llm.client import _retry_instruction
    message = _retry_instruction('finish_reason=length', stage)
    assert 'complete' in message
    assert '25 words' not in message


def test_edge_evidence_cannot_be_one_character_overlap():
    raw, obj = fixture()
    spans = [{'sentence_id': 'S1', 'start': 3, 'end': 4, 'text': 't'},
             {'sentence_id': 'S1', 'start': 21, 'end': 22, 'text': 'w'}]
    obj['argument_edges'] = [{'source_ids': ['P01'], 'target_id': 'P02', 'relation': 'SUPPORT',
        'source_spans': spans, 'evidence_sentence_ids': ['S1'], 'surface_markers': [], 'justification': 'Invalid partial evidence.'}]
    with pytest.raises(ValueError, match='source and target'):
        validate_graph(obj, raw)


def test_failed_provider_calls_are_preserved_in_trace(tmp_path):
    from src.llm.client import Client
    from src.llm.config import ModelConfig
    from src.atomic_v3_runner import extract, ExtractionError

    class Transport:
        def complete(self, payload):
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}],
                    'usage': {'total_tokens': 123}}

    client = Client(ModelConfig(name='fixture', max_attempts=2, backoff_seconds=0),
        tmp_path / 'cache.db', tmp_path / 'audit.jsonl', transport=Transport(), raw_debug_path=tmp_path / 'raw.jsonl')
    with pytest.raises(ExtractionError) as error:
        extract(client, 'Residents might object.', 'demo')
    trace = error.value.trace
    assert len(trace) == 1 and 'error' in trace[0]
    assert len(trace[0]['attempts']) == 2
    assert sum(r['response']['usage']['total_tokens'] for r in trace[0]['responses']) == 246


def test_edge_provenance_is_derived_from_locked_endpoints():
    from src.atomic_v3 import materialize_edges
    raw, obj = fixture()
    payload = {'discourse_edges': [], 'argument_edges': [{'source_ids': ['P01'], 'target_id': 'P02',
        'relation': 'SUPPORT', 'additional_evidence': [], 'surface_markers': [], 'justification': 'Reason given by author.'}]}
    edges = materialize_edges(payload, obj)
    assert edges['argument_edges'][0]['source_spans'] == [p['source_spans'][0] for p in obj['propositions']]
    assert edges['argument_edges'][0]['evidence_sentence_ids'] == ['S1']
    validate_graph({**obj, **edges}, raw)


def test_manual_semantic_issues_block_final_graph_without_losing_draft(tmp_path):
    from src.atomic_v3_runner import apply_manual_review
    from src.io_utils import write_json
    raw, graph = fixture()
    write_json(tmp_path / 'inputs.json', [{'sample_id': 'demo', 'comment': raw}])
    write_json(tmp_path / 'report.json', {'valid': 1, 'failed': 0, 'samples': [{'sample_id': 'demo', 'valid': True}]})
    write_json(tmp_path / 'graphs' / 'demo.json', graph)
    issue = {'sample_id': 'demo', 'stage': 'edges', 'node_ids': ['P01'], 'edge_ids': [],
        'rule': 'SEMANTIC_REVIEW', 'source_quote': 'If the rule changes',
        'explanation': 'An ambiguity remains.', 'proposed_action': 'NEEDS_HUMAN_REVIEW'}
    report = apply_manual_review(tmp_path, [issue])
    assert report['valid'] == 0 and report['failed'] == 1
    assert report['automatic_valid'] == 1
    assert not (tmp_path / 'graphs' / 'demo.json').exists()
    assert (tmp_path / 'drafts' / 'graphs' / 'demo.json').exists()
