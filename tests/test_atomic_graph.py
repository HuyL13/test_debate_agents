from copy import deepcopy

import pytest

from src.atomic_graph import validate_graph, linearize, select_samples, execute
from src.data.loader import load_split


def graph():
    return {
        'schema_version': '2.0', 'document_id': 'demo',
        'sentences': [{'id': 'S1', 'text': 'A happened, therefore B happened.'}],
        'propositions': [
            {'id': 'P01', 'text': 'B happened.', 'source_sentence_ids': ['S1'], 'mode': 'ASSERTED'},
            {'id': 'P02', 'text': 'A happened.', 'source_sentence_ids': ['S1'], 'mode': 'ASSERTED'},
            {'id': 'P03', 'text': 'A happened.', 'source_sentence_ids': ['S1'], 'mode': 'HEDGED'}],
        'references': [], 'discourse_edges': [],
        'argument_edges': [{'source_ids': ['P02', 'P03'], 'target_id': 'P01',
                            'relation': 'SUPPORT', 'evidence_sentence_ids': ['S1']}],
    }


def test_topological_order_preserves_joint_support_and_modes():
    obj = graph()
    validate_graph(obj, obj['sentences'][0]['text'], 'demo')
    text = linearize(obj)
    assert 'P02 | P03 | P01' in text
    assert '{P02,P03} --SUPPORT--> P01' in text
    assert '[HEDGED]' in text
    changed = deepcopy(obj)
    changed['propositions'].reverse()
    assert linearize(changed) == text


@pytest.mark.parametrize('mutation', ['cycle', 'candidate', 'fabricated', 'wrong_connective', 'document'])
def test_rejects_invalid_graph(mutation):
    obj = graph()
    original = obj['sentences'][0]['text']
    if mutation == 'cycle':
        obj['argument_edges'].append({'source_ids': ['P01'], 'target_id': 'P02',
                                     'relation': 'SUPPORT', 'evidence_sentence_ids': ['S1']})
    elif mutation == 'candidate':
        obj['candidate_edges'] = []
    elif mutation == 'fabricated':
        obj['sentences'][0]['text'] = 'Invented evidence.'
    elif mutation == 'document':
        obj['document_id'] = 'other'
    else:
        obj['discourse_edges'] = [{'source_ids': ['P02'], 'target_id': 'P01',
            'relation': 'CAUSAL', 'connective': 'if', 'origin': 'EXPLICIT', 'evidence_sentence_ids': ['S1']}]
    with pytest.raises(ValueError):
        validate_graph(obj, original, 'demo')


def test_disconnected_graph_and_reproducible_selection():
    obj = graph()
    obj['argument_edges'] = []
    validate_graph(obj, obj['sentences'][0]['text'], 'demo')
    assert 'P01 | P02 | P03' in linearize(obj)
    samples = load_split('data/cocolofa/test.json')
    chosen = select_samples(samples, 10, 42)
    assert len(chosen) == len({s.sample_id for s in chosen}) == 10
    assert chosen == select_samples(samples, 10, 42)


def test_execute_saves_graphs_without_sending_labels(tmp_path):
    import json
    from types import SimpleNamespace

    class Client:
        def generate(self, **kwargs):
            payload = json.loads(kwargs['user_prompt'])
            assert set(payload) == {'document_id', 'target'}
            obj = {'schema_version': '2.0', 'document_id': payload['document_id'],
                'sentences': [{'id': 'S1', 'text': payload['target']}],
                'propositions': [{'id': 'P01', 'text': payload['target'],
                    'source_sentence_ids': ['S1'], 'mode': 'ASSERTED'}],
                'references': [], 'discourse_edges': [], 'argument_edges': []}
            kwargs['validator'](obj)
            return SimpleNamespace(output=obj)

    report = execute({'data_dir': 'data/cocolofa', 'split': 'test'}, tmp_path, client=Client())
    assert report['valid'] == 10
    assert report['failed'] == 0
    assert len(list((tmp_path / 'graphs').glob('*.json'))) == 10
    assert len(list((tmp_path / 'linearized').glob('*.txt'))) == 10
    assert 'fallacy' not in (tmp_path / 'inputs.json').read_text(encoding='utf-8')
    with pytest.raises(ValueError, match='already contains'):
        execute({'data_dir': 'data/cocolofa', 'split': 'test'}, tmp_path, seed=43, client=Client())


