import pytest

from src.discourse_classification.graph import build_graph
from src.discourse_classification.graph import StanzaParser
from src.discourse_classification.patterns import retrieve
from src.discourse_classification.pipeline import candidate_status, validate_evidence, ground_evidence
from src.discourse_classification.data import partition
from src.discourse_classification.pipeline import classify_legacy as classify
from src.discourse_classification.runner import execute
from types import SimpleNamespace
import json


def test_short_slope_and_single_clause_tradition_are_retrieved():
    for text, label in [
        ("What's next after gay acceptance? Will it be animal marriage!", 'Slippery Slope'),
        ('We should keep it because we have done it for generations.', 'Appeal to Tradition'),
        ("Don't cut any trees down or cut them all down.", 'False Dilemma'),
    ]:
        graph = build_graph(text)
        assert label in {c['label'] for c in retrieve(graph)}
        for node in graph['propositions']:
            assert text[node['char_start']:node['char_end']] == node['text']


def test_required_false_cannot_be_offset_and_uncertain_is_not_confirmed():
    assert candidate_status({'ownership': 'USES', 'mechanism': 'ABSENT', 'defect': None}) == 'rejected'
    assert candidate_status({'ownership': 'USES', 'mechanism': 'UNCLEAR', 'defect': None}) == 'uncertain'
    assert candidate_status({'ownership': 'USES', 'mechanism': 'PRESENT', 'defect': 'PRESENT'}) == 'confirmed'


def test_evidence_rejects_invented_or_wrong_offsets():
    validate_evidence({'comment': 'Only two choices.'}, [{'source': 'comment', 'start': 0, 'end': 4, 'text': 'Only'}])
    with pytest.raises(ValueError):
        validate_evidence({'comment': 'Only two choices.'}, [{'source': 'comment', 'start': 1, 'end': 5, 'text': 'Only'}])


def test_code_grounds_quotes_without_requiring_llm_character_counting():
    result = {'evidence': [{'source': 'comment', 'text': 'two choices', 'start': 99, 'end': 120}]}
    ground_evidence({'comment': 'Only two choices.'}, result)
    assert result['evidence'] == [{'source': 'comment', 'text': 'two choices', 'start': 5, 'end': 16}]
    nested = {'results': [{'evidence': [{'source': 'comment', 'text': 'Only'}]}]}
    ground_evidence({'comment': 'Only two choices.'}, nested)
    assert nested['results'][0]['evidence'][0]['end'] == 4
    with pytest.raises(ValueError, match='exact substring'):
        ground_evidence({'comment': 'Only two choices.'}, {'evidence': [{'source': 'comment', 'text': 'Three choices'}]})


def test_partition_never_splits_an_article_and_is_reproducible():
    rows = [{'sample_id': str(i), 'article_id': i // 2} for i in range(20)]
    design, validation = partition(rows, .2, 42)
    assert not {r['article_id'] for r in design} & {r['article_id'] for r in validation}
    assert len(design) + len(validation) == 20
    assert (design, validation) == partition(rows, .2, 42)


class FakeClient:
    def __init__(self, mode):
        self.mode = mode

    def generate(self, **kwargs):
        payload = json.loads(kwargs['user_prompt'])
        if kwargs['metadata']['stage'] in ('discourse_verify', 'discourse_decision_verify'):
            assert kwargs['schema']['properties']['results']['type'] == 'object'
            assert all('defect' not in s['properties'] for s in kwargs['schema']['properties']['results']['properties'].values())
            assert all('defect' not in v for v in payload['constraints'].values())
            output = {'results': {c['candidate_id']: {'ownership': 'USES',
                'mechanism': 'PRESENT',
                'premise_node_ids': c['nodes'][:1], 'conclusion_node_ids': c['nodes'][-1:],
                'evidence': [{'source': 'comment', 'start': 0, 'end': 7, 'text': 'Natural'}],
                'reason': 'Naturalness used as proof.'}
                for c in payload['candidates']}}
        elif kwargs['metadata']['stage'].endswith('_defect'):
            output = {'results': {c['candidate_id']: {
                'defect': 'ABSENT' if self.mode == 'reject' and kwargs['metadata']['stage'] == 'discourse_verify_defect' else 'PRESENT',
                'reason': 'Naturalness substitutes for justification.',
                'evidence': [{'source': 'comment', 'text': 'Natural'}]}
                for c in payload['candidates']}}
        else:
            if kwargs['metadata']['stage'] == 'discourse_recovery':
                assert len(kwargs['schema']['properties']['label']['enum']) == 8
            output = {'label': 'Appeal to Nature', 'reason': 'Naturalness used as proof.', 'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P1'],
                'evidence': [{'source': 'comment', 'start': 0, 'end': 7, 'text': 'Natural'}]}
        if kwargs.get('validator'):
            kwargs['validator'](output)
        return SimpleNamespace(output=output)


def test_rejected_candidates_trigger_recovery_instead_of_argmax_default():
    result = classify(FakeClient('reject'), {'comment': 'Natural products are good.'}, '1', implicit=False)
    assert result['label'] == 'Appeal to Nature'
    assert result['decision_mode'] == 'recovery'
    assert result['verification'][0]['status'] == 'rejected'
    assert result['verification'][-1]['status'] == 'confirmed'


def test_confirmed_single_label_needs_no_extra_classification_call():
    result = classify(FakeClient('confirm'), {'comment': 'Natural products are good.'}, '1', implicit=False)
    assert result['decision_mode'] == 'verified'
    assert result['calls'] == 2  # mechanism batch, then defect batch; no final classifier


def test_recovery_cannot_invent_a_label_without_structural_anchor():
    class UnanchoredClient(FakeClient):
        def generate(self, **kwargs):
            if kwargs['metadata']['stage'] == 'discourse_recovery':
                output = {'label': 'Hasty Generalization', 'reason': 'Invented population inference.',
                    'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P1'],
                    'evidence': [{'source': 'comment', 'text': 'Natural'}]}
                kwargs['validator'](output)
                return SimpleNamespace(output=output)
            return super().generate(**kwargs)
    with pytest.raises(ValueError, match='structural anchor') as failure:
        classify(UnanchoredClient('reject'), {'comment': 'Natural products are good.'}, '1', implicit=False)
    assert failure.value.discourse_trace['candidates'][0]['label'] == 'Appeal to Nature'
    assert failure.value.discourse_trace['verification'][0]['status'] == 'rejected'


def test_recovery_must_pass_verification_not_self_declared_presence():
    class RejectedRecovery(FakeClient):
        def generate(self, **kwargs):
            response = super().generate(**kwargs)
            if kwargs['metadata']['stage'] == 'discourse_decision_verify':
                r = response.output['results']['RECOVERY']
                r.update(ownership='MENTIONS_OR_REJECTS', defect=None)
            return response
    with pytest.raises(ValueError, match='failed ownership'):
        classify(RejectedRecovery('reject'), {'comment': 'Natural products are good.'}, '1', implicit=False)


def test_uncertain_recovery_cannot_replace_evidence_with_empty_list():
    class EmptyRecovery(FakeClient):
        def generate(self, **kwargs):
            response = super().generate(**kwargs)
            if kwargs['metadata']['stage'] == 'discourse_decision_verify':
                response.output['results']['RECOVERY'].update(defect='UNCLEAR', evidence=[])
            return response
    with pytest.raises(ValueError, match='evidence'):
        classify(EmptyRecovery('reject'), {'comment': 'Natural products are good.'}, '1', implicit=False)


def test_runner_resume_and_minimal_artifacts(tmp_path):
    data = tmp_path / 'train.json'
    data.write_text(json.dumps([{'id': '1', 'article_id': 1, 'comment': 'Natural products are good.', 'label': 'Appeal to Nature'}]))
    config = {'input': str(data), 'context': 'comment_only', 'method': 'rules', 'engine': 'legacy', 'implicit': False,
              'model': {}, 'output_root': str(tmp_path / 'runs'), 'parser': 'rules'}
    report = execute(config, output='smoke', client=FakeClient('confirm'))
    assert report['accuracy'] == 1
    assert report['coverage']['Appeal to Nature']['covered'] == 1
    assert not (tmp_path / 'runs/smoke/api_calls.jsonl').exists()
    execute(config, output='smoke', client=FakeClient('reject'), resume=True)
    assert len((tmp_path / 'runs/smoke/results.jsonl').read_text().splitlines()) == 1
    with pytest.raises(ValueError, match='Resume'):
        execute({**config, 'implicit': True}, output='smoke', client=FakeClient('confirm'), resume=True)


def test_stanza_subordinate_marker_stays_with_its_clause():
    # Real-model integration regression; skip only when model assets are unavailable.
    from pathlib import Path
    if not Path('cache/stanza/en/constituency').exists():
        pytest.skip('Stanza model assets not installed')
    parser = StanzaParser('cache/stanza')
    graph = build_graph('We should keep it because we have done it for generations.', parser)
    assert all(n['text'].lower() != 'because' for n in graph['propositions'])
    relation = next(r for r in graph['relations'] if r['type'] == 'JUSTIFICATION')
    nodes = {n['id']: n['text'] for n in graph['propositions']}
    assert 'for generations' in nodes[relation['arg1']]
    assert 'keep it' in nodes[relation['arg2']]
    conditional = build_graph('If we allow this, society will collapse.', parser)
    assert all(n['text'].lower() != 'if' for n in conditional['propositions'])
    assert any(r['type'] == 'CONDITION' for r in conditional['relations'])
    embedded = build_graph("Assuming the authorities are being malicious instead of them allocating resources in an intelligent way isn't sensible.", parser)
    assert all(n['text'] != 'Assuming' for n in embedded['propositions'])
    for text, kind, premise, conclusion in [
        ('Experts know better. Because it is natural, it is good.', 'JUSTIFICATION', 'natural', 'good'),
        ('Experts know better. If we allow this, society will collapse.', 'CONDITION', 'allow', 'collapse'),
        ('Society will collapse if we allow this.', 'CONDITION', 'allow', 'collapse'),
    ]:
        scoped = build_graph(text, parser)
        ns = {n['id']: n['text'] for n in scoped['propositions']}
        relations = [r for r in scoped['relations'] if r['type'] == kind]
        assert len(relations) == 1
        assert premise in ns[relations[0]['arg1']]
        assert conclusion in ns[relations[0]['arg2']]
    coordinated = build_graph('We should stop because it is unsafe and because experts say so.', parser)
    reasons = [r for r in coordinated['relations'] if r['type'] == 'JUSTIFICATION']
    assert len(reasons) == 2
    assert {r['arg2'] for r in reasons} == {'P1'}


def test_resume_rejects_changed_effective_model_and_recovers_torn_tail(tmp_path, monkeypatch):
    data = tmp_path / 'train.json'
    data.write_text(json.dumps([{'id': '1', 'comment': 'Natural products are good.', 'label': 'Appeal to Nature'}]))
    config = {'input': str(data), 'context': 'comment_only', 'method': 'rules', 'engine': 'legacy', 'implicit': False,
              'model': {'name_env': 'TEST_DISCOURSE_MODEL'}, 'output_root': str(tmp_path / 'runs'), 'parser': 'rules'}
    monkeypatch.setenv('TEST_DISCOURSE_MODEL', 'first-model')
    execute(config, output='smoke', client=FakeClient('confirm'))
    path = tmp_path / 'runs/smoke/results.jsonl'
    with path.open('a') as stream:
        stream.write('{"sample_id":')
    execute(config, output='smoke', client=FakeClient('confirm'), resume=True)
    assert len(path.read_text().splitlines()) == 1
    monkeypatch.setenv('TEST_DISCOURSE_MODEL', 'second-model')
    with pytest.raises(ValueError, match='Resume'):
        execute(config, output='smoke', client=FakeClient('confirm'), resume=True)
