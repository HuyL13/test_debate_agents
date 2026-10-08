import pytest

from src.discourse_classification.graph import build_graph
from src.discourse_classification.patterns import retrieve
from src.discourse_classification.pipeline import validate_slope_evidence


def test_causal_predicate_stays_in_one_proposition():
    text = 'Allowing crimes to go unchecked is just going to cause more crimes of this type.'
    graph = build_graph(text)
    assert [n['text'] for n in graph['propositions']] == [text]
    assert not any(c['label'] == 'Slippery Slope' for c in retrieve(graph))


def test_compressed_extreme_warning_is_anchored_without_splitting_predicate():
    text = 'Allowing this policy will lead to silencing all journalists.'
    graph = build_graph(text)
    assert len(graph['propositions']) == 1
    assert any(c['label'] == 'Slippery Slope' for c in retrieve(graph))


def test_tradition_candidate_includes_local_historical_reference():
    graph = build_graph("This practice is a story as old as time. It's almost tradition. People accept that things have always been this way.")
    cs = [c for c in retrieve(graph) if c['label'] == 'Appeal to Tradition']
    assert any({'P1', 'P2', 'P3'} <= set(c['nodes']) for c in cs)


def test_slope_needs_action_and_escalation_quotes_in_candidate_roles():
    text = 'This policy will lead to silencing.'
    graph = build_graph(text)
    candidate = {'label': 'Slippery Slope', 'nodes': ['P1']}
    result = {'mechanism': 'PRESENT', 'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P1'],
              'evidence': [{'source': 'comment', 'start': 0, 'end': 11, 'text': 'This policy', 'role': 'ACTION'}]}
    with pytest.raises(ValueError, match='escalation'):
        validate_slope_evidence(candidate, result, graph)
    result['evidence'].append({'source': 'comment', 'start': 25, 'end': 34,
                              'text': 'silencing', 'role': 'ESCALATION_OR_EXTREME'})
    validate_slope_evidence(candidate, result, graph)
    result['evidence'][0] = {**result['evidence'][1], 'role': 'ACTION'}
    with pytest.raises(ValueError, match='distinct'):
        validate_slope_evidence(candidate, result, graph)
    result['conclusion_node_ids'] = ['P2']
    with pytest.raises(ValueError):
        validate_slope_evidence(candidate, result, graph)
