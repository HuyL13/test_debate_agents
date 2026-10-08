import pytest

from src.discourse_classification.graph import build_graph, StanzaParser
from src.discourse_classification.patterns import retrieve
from src.discourse_classification.pipeline import validate_anchor


def labels(text, parser=None):
    return {c['label'] for c in retrieve(build_graph(text, parser))}


def test_enumeration_is_not_choice_even_with_modal_verb():
    text = 'We should address climate change, world hunger, or economic crises.'
    graph = build_graph(text)
    assert not any(r['type'] == 'ALTERNATIVE' for r in graph['relations'])
    assert 'False Dilemma' not in labels(text)
    assert 'False Dilemma' in labels("You either ban reporting or you allow it.")


def test_keywords_without_inferential_anchor_do_not_create_candidates():
    for text in ['Governments never tell us anything.', 'Nature is beautiful.',
                 'This is a tradition.', 'Everyone is here.', 'Experts arrived today.']:
        assert not retrieve(build_graph(text))


def test_causal_warning_has_anchor_not_sample_generalization():
    text = 'The regulation of NGOs is necessary. Though it can lead to silencing.'
    candidates = retrieve(build_graph(text))
    assert any(c['label'] == 'Slippery Slope' and len(c['nodes']) >= 2 for c in candidates)
    assert not any(c['label'] == 'Hasty Generalization' for c in candidates)
    text = 'This one incident proves that all governments abuse power.'
    assert 'Hasty Generalization' in labels(text)


def test_escalation_and_question_chain_are_grouped():
    text = 'The movement takes more and more, until one group holds all power.'
    graph = build_graph(text)
    assert any(r['type'] in ('SEQUENCE', 'CONSEQUENCE') for r in graph['relations'])
    assert 'Slippery Slope' in {c['label'] for c in retrieve(graph)}
    questions = 'What comes next? Will they jail people on accusation? Will they execute them before trial?'
    candidates = retrieve(build_graph(questions))
    assert any(c['label'] == 'Slippery Slope' and len(c['nodes']) == 3 for c in candidates)


def test_connective_only_spans_are_merged_without_losing_source_text():
    text = 'This matters but if it fails, we lose.'
    parser = lambda _: [(0, 13, 0), (13, 16, 0), (17, len(text), 0)]
    graph = build_graph(text, parser)
    assert all(n['text'].lower() not in ('but', 'or', 'if') for n in graph['propositions'])
    for n in graph['propositions']:
        assert text[n['char_start']:n['char_end']] == n['text']


def test_verifier_cannot_confirm_mechanism_outside_candidate():
    candidate = {'label': 'Slippery Slope', 'nodes': ['P1', 'P2']}
    result = {'mechanism': 'PRESENT', 'premise_node_ids': ['P1'], 'conclusion_node_ids': ['P3'],
              'bridge_type': 'ACTION_TO_CONSEQUENCE'}
    with pytest.raises(ValueError, match='candidate'):
        validate_anchor(candidate, result)
    result['conclusion_node_ids'] = ['P2']
    validate_anchor(candidate, result)
    result['bridge_type'] = 'SAMPLE_TO_POPULATION'
    with pytest.raises(ValueError, match='bridge'):
        validate_anchor(candidate, result)


def test_real_stanza_lists_connectives_and_escalation():
    from pathlib import Path
    if not Path('cache/stanza/en/constituency').exists():
        pytest.skip('Stanza assets not installed')
    parser = StanzaParser('cache/stanza')
    causal_text = 'Allowing crimes like this to go unchecked is just going to cause more crimes of this type.'
    causal = build_graph(causal_text, parser)
    assert [n['text'] for n in causal['propositions']] == [causal_text]
    enumeration = build_graph("Let's not lose sight of bigger issues like climate change, world hunger, or economic crises.", parser)
    assert not any(r['type'] == 'ALTERNATIVE' for r in enumeration['relations'])
    assert 'False Dilemma' not in {c['label'] for c in retrieve(enumeration)}
    escalation = build_graph('I can see the movement taking more and more, until women hold the power in society and men will go on strike for equal representation.', parser)
    assert any(c['label'] == 'Slippery Slope' and len(c['nodes']) >= 3 for c in retrieve(escalation))
    compound = build_graph('Not only that but if journalists are being targeted who will investigate crimes?', parser)
    assert all(not n['text'].strip().lower() in ('but', 'or', 'if') for n in compound['propositions'])
    assert all(not n['text'].strip().lower().startswith('not only that') or 'journalists' in n['text']
               for n in compound['propositions'])
    conditional = build_graph('If this policy fails, then we should try another approach.', parser)
    ns = {n['id']: n['text'] for n in conditional['propositions']}
    assert all(any(c.isalnum() for c in n) for n in ns.values())
    relation = next(r for r in conditional['relations'] if r['type'] == 'CONDITION')
    assert 'policy fails' in ns[relation['arg1']]
    assert 'try another approach' in ns[relation['arg2']]
