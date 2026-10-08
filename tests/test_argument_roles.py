import pytest
import json
from types import SimpleNamespace

from src.discourse_classification.graph import build_graph
from src.discourse_classification.roles import match_arguments, select_candidate
from src.discourse_classification.pipeline import classify
from src.discourse_classification.runner import summarize, execute


def test_role_schema_rejects_unknown_kind_and_extra_family_fields():
    from src.schemas import validate_output
    from src.discourse_classification.roles import extraction_schema
    valid = argument('GENERALIZATION', [ref('one case', 'SAMPLE')])
    validate_output({'arguments': [valid]}, extraction_schema())
    for invalid in ({**valid, 'kind': 'UNKNOWN'}, {**valid, 'basis': 'N/A'}):
        with pytest.raises(ValueError):
            validate_output({'arguments': [invalid]}, extraction_schema())


def test_extraction_demonstrations_are_grounded_train_examples():
    from src.discourse_classification.examples import role_examples
    from src.discourse_classification.roles import extraction_schema
    from src.schemas import validate_output
    from pathlib import Path
    train = {r['sample_id']: r for r in json.loads(Path('data/cocolofa/classification/train.json').read_text(encoding='utf-8'))}
    examples = role_examples()
    assert examples
    for ex in examples:
        assert ex['comment'] == train[ex['train_sample_id']]['comment']
        assert not {'gold', 'label', 'prediction'} & set(ex)
        validate_output(ex['output'], extraction_schema())
        candidates = match(ex['comment'], ex['output']['arguments'])
        assert candidates
        assert all(e['text'] == ex['comment'][e['start']:e['end']]
                   for c in candidates for e in c['evidence'])


def test_demonstrations_exclude_evaluation_articles():
    from src.discourse_classification.examples import role_examples
    assert all(ex['train_sample_id'].split(':')[0] not in {'327', '449'}
               for ex in role_examples(excluded_articles={327, 449}))


def test_completion_includes_postposed_graph_support():
    from src.discourse_classification.roles import completion_subgraph, validate_completion
    text = 'We should keep it because it has always been done.'
    graph = build_graph(text)
    nodes, relations = completion_subgraph(graph, ['P1'])
    assert {n['id'] for n in nodes} == {'P1', 'P2'}
    assert relations and relations[0]['type'] == 'JUSTIFICATION'
    a = argument('SOURCE_JUSTIFICATION', [ref('We should keep it', 'CLAIM'), ref('it has always been done', 'BASIS')], basis='HISTORY')
    validate_completion(graph, {'comment': text}, ['P1'], {'arguments': [a]})


def test_completion_keeps_existing_argument_backbone_when_support_is_farther_away():
    from src.discourse_classification.roles import completion_subgraph, validate_completion, validate_extraction
    text = 'One poster did not affect me. Detail two. Detail three. Detail four. Detail five. Detail six. Detail seven. It cannot affect anyone. They should stop using posters.'
    graph = build_graph(text)
    a = argument('GENERALIZATION', [ref('One poster did not affect me', 'SAMPLE'),
        ref('anyone', 'POPULATION'), ref('It cannot affect anyone', 'CONCLUSION')])
    validate_extraction(graph, {'comment': text}, {'arguments': [a]})
    focus = [graph['propositions'][-1]['id']]
    nodes, _ = completion_subgraph(graph, focus, [a])
    assert graph['propositions'][0]['id'] in {n['id'] for n in nodes}
    assert len(nodes) <= 8
    b = {**a, 'evidence': a['evidence'] + [ref('They should stop using posters', 'CONCLUSION')]}
    validate_completion(graph, {'comment': text}, focus, {'arguments': [b]}, [a])


def test_primary_extraction_failure_retains_graph_for_inspection():
    class FailingClient:
        def generate(self, **kwargs):
            raise ValueError('Invalid role JSON')
    with pytest.raises(ValueError) as captured:
        classify(FailingClient(), {'comment': 'A complete sentence.'}, '1', method='rules')
    assert captured.value.discourse_trace['graph']['propositions']
    assert captured.value.discourse_trace['calls'] == 1


def test_unrepresented_causal_graph_bridge_triggers_bounded_endpoint_audit():
    a = argument('CONSEQUENCE', [ref('New restrictions apply', 'ACTION'),
        ref('It can lead to silencing', 'OUTCOME')], progression='ADVERSE')
    class EndpointClient(RoleClient):
        def generate(self, **kwargs):
            if kwargs['metadata']['stage'] == 'discourse_argument_completion':
                payload = json.loads(kwargs['user_prompt'])
                assert 'OUTCOME' in payload['focus_roles'][payload['focus_nodes'][0]]
                self.arguments = [a]
            return super().generate(**kwargs)
    result = classify(EndpointClient([]), {'comment': 'New restrictions apply. It can lead to silencing.'}, '1', method='rules')
    assert result['label'] == 'Slippery Slope'
    assert result['calls'] == 2
    assert result['role_completion_status'] == 'completed'


def test_covered_ordinary_causal_relation_does_not_trigger_another_extraction():
    from src.discourse_classification.roles import coverage_focus, validate_extraction
    text = 'Rain falls. It can lead to wet roads.'
    graph = build_graph(text)
    a = argument('CONSEQUENCE', [ref('Rain falls', 'ACTION'), ref('wet roads', 'OUTCOME')], progression='ORDINARY')
    validate_extraction(graph, {'comment': text}, {'arguments': [a]})
    assert coverage_focus(graph, [a]) == ([], {})


def test_transition_question_is_not_an_uncovered_event_anchor():
    from src.discourse_classification.roles import coverage_focus, validate_extraction
    text = 'What comes next? Will we jail people? After that will we execute them?'
    graph = build_graph(text)
    a = argument('CONSEQUENCE', [ref('Will we jail people?', 'ACTION'),
        ref('After that will we execute them?', 'OUTCOME')], progression='ESCALATING')
    validate_extraction(graph, {'comment': text}, {'arguments': [a]})
    assert coverage_focus(graph, [a]) == ([], {})


def ref(text, role):
    return {'source': 'comment', 'text': text, 'role': role}


def argument(kind, evidence, **fields):
    return {'kind': kind, 'stance': 'USES', 'relation_status': 'EXPLICIT', 'evidence': evidence, **fields}


def match(text, args):
    return match_arguments(build_graph(text), {'comment': text}, args)


def test_causal_chain_is_ordered_by_source_not_extraction_order():
    text = 'Allow this policy. Next jail people. Then execute them.'
    args = [argument('CONSEQUENCE', [ref('execute them', 'OUTCOME'), ref('Allow this policy', 'ACTION'),
             ref('jail people', 'STEP')], progression='ESCALATING')]
    cs = match(text, args)
    assert cs[0]['label'] == 'Slippery Slope'
    assert cs[0]['nodes'] == ['P1', 'P2', 'P3']
    assert select_candidate(cs)['label'] == 'Slippery Slope'


def test_ordered_question_events_supply_progression_support():
    text = 'Will they ban letters? After that will they abolish elections?'
    a = argument('CONSEQUENCE', [ref('Will they ban letters?', 'ACTION'),
        ref('After that will they abolish elections?', 'OUTCOME')], progression='ADVERSE')
    cs = match(text, [a])
    assert cs[0]['relations']
    assert cs[0]['support'][0] == 2


def test_general_statement_without_sample_does_not_match_hasty():
    text = 'All governments hide information.'
    args = [argument('GENERALIZATION', [ref('All governments', 'POPULATION'),
                                       ref(text, 'CONCLUSION')])]
    assert not match(text, args)


def test_sample_repetition_is_not_a_broader_conclusion():
    text = 'One case happened. People were present.'
    a = argument('GENERALIZATION', [ref('One case happened', 'SAMPLE'), ref('People', 'POPULATION'),
                                   ref('One case happened', 'CONCLUSION')])
    assert not match(text, [a])


def test_ordinary_causal_forecast_does_not_match_slope():
    text = 'Unchecked crimes cause more crimes.'
    args = [argument('CONSEQUENCE', [ref('Unchecked crimes', 'ACTION'), ref('more crimes', 'OUTCOME')], progression='ORDINARY')]
    assert not match(text, args)


def test_two_exhaustive_alternatives_are_already_a_choice_claim():
    text = 'Either obey or leave.'
    a = argument('CHOICE', [ref('obey', 'ALTERNATIVE'), ref('leave', 'ALTERNATIVE')], exhaustivity='EXHAUSTIVE')
    assert match(text, [a])[0]['label'] == 'False Dilemma'


def test_alternative_bridge_is_independent_of_role_quote_order():
    from src.discourse_classification.roles import bridge_path
    graph = {'relations': [{'id': 'R1', 'type': 'ALTERNATIVE', 'arg1': 'P1', 'arg2': 'P2'}]}
    assert bridge_path(graph, 'False Dilemma', {'P2'}, {'P1'}, {'P1', 'P2'}) == ['R1']


def test_criticized_historical_reasoning_remains_a_dataset_candidate():
    text = 'They accept this because it has always been done. I disagree.'
    a = argument('SOURCE_JUSTIFICATION', [ref('it has always been done', 'BASIS'), ref('They accept this', 'CLAIM')], basis='HISTORY')
    a['stance'] = 'CRITICIZES'
    cs = match(text, [a])
    assert cs[0]['label'] == 'Appeal to Tradition'
    assert cs[0]['stance'] == 'CRITICIZES'


def test_quotes_cannot_be_invented_or_reused_for_distinct_roles():
    text = 'Some products are natural and good.'
    a = argument('SOURCE_JUSTIFICATION', [ref('natural', 'BASIS'), ref('invented claim', 'CLAIM')], basis='NATURE')
    with pytest.raises(ValueError, match='substring'):
        match(text, [a])
    a['evidence'][1] = ref('natural', 'CLAIM')
    assert not match(text, [a])


def test_duplicate_arguments_do_not_create_duplicate_label_candidates():
    text = 'Natural products are good.'
    a = argument('SOURCE_JUSTIFICATION', [ref('Natural', 'BASIS'), ref('good', 'CLAIM')], basis='NATURE')
    assert len(match(text, [a, a])) == 1


def test_dedup_keeps_strongest_support_regardless_of_extraction_order():
    text = 'Natural products are good.'
    a = argument('SOURCE_JUSTIFICATION', [ref('Natural', 'BASIS'), ref('good', 'CLAIM')], basis='NATURE')
    weak = {**a, 'relation_status': 'UNCLEAR'}
    assert match(text, [weak, a])[0]['support'] == match(text, [a, weak])[0]['support'] == [2, 0, 1]


def test_graph_support_must_connect_defining_roles_not_two_action_quotes():
    text = 'Allow this policy. Next jail people. Then execute them. We must be careful.'
    a = argument('CONSEQUENCE', [ref('jail people', 'ACTION'), ref('execute them', 'ACTION'),
                               ref('We must be careful', 'OUTCOME')], progression='ESCALATING')
    assert not match(text, [a])


@pytest.mark.parametrize('action,outcome', [
    ('What happens next?', 'imprison people'),
    ('ban meetings', 'We must be careful.'),
    ('ban meetings', 'I hope we will think about this and discuss it.'),
])
def test_discussion_and_transition_quotes_are_not_consequence_events(action, outcome):
    text = f'{action} Then {outcome}'
    a = argument('CONSEQUENCE', [ref(action, 'ACTION'), ref(outcome, 'OUTCOME')], progression='ESCALATING')
    assert not match(text, [a])


def test_careful_advice_after_contrast_does_not_trigger_completion():
    from src.discourse_classification.roles import uncovered_claims
    text = 'We want justice but we must be careful when changing protections.'
    assert uncovered_claims(build_graph(text), []) == []


def test_completion_must_cover_its_focus_and_stay_in_subgraph():
    from src.discourse_classification.roles import validate_completion
    text = 'Old detail. Another detail. Ignore one complaint and expect further complaints. Institutional censorship is worse. We must protect public access.'
    graph = build_graph(text)
    sources = {'comment': text}
    focus = [graph['propositions'][-1]['id']]
    a = argument('CONSEQUENCE', [ref('Ignore one complaint', 'ACTION'), ref('further complaints', 'OUTCOME')], progression='ORDINARY')
    with pytest.raises(ValueError, match='focus conclusion'):
        validate_completion(graph, sources, focus, {'arguments': [a]})
    a['evidence'].append(ref('We must protect public access', 'CLAIM'))
    validate_completion(graph, sources, focus, {'arguments': [a]})
    a['evidence'][0] = ref('Old detail', 'ACTION')
    with pytest.raises(ValueError, match='subgraph'):
        validate_completion(graph, sources, focus, {'arguments': [a]})


def test_generation_validator_rejects_collapsed_roles_for_retry():
    from src.discourse_classification.roles import validate_extraction
    text = 'An old practice. They accept it.'
    a = argument('SOURCE_JUSTIFICATION', [ref('An old practice', 'BASIS'), ref('An old practice', 'CLAIM')], basis='HISTORY')
    with pytest.raises(ValueError, match='distinct'):
        validate_extraction(build_graph(text), {'comment': text}, {'arguments': [a]})
    a['evidence'][1] = ref('They accept it', 'CLAIM')
    validate_extraction(build_graph(text), {'comment': text}, {'arguments': [a]})


def test_generation_validator_rejects_incomplete_argument_not_empty_extraction():
    from src.discourse_classification.roles import validate_extraction
    text = 'One event. Another event.'
    a = argument('CONSEQUENCE', [ref('One event', 'STEP'), ref('Another event', 'STEP')], progression='ORDINARY')
    with pytest.raises(ValueError, match='ACTION.*OUTCOME'):
        validate_extraction(build_graph(text), {'comment': text}, {'arguments': [a]})
    validate_extraction(build_graph(text), {'comment': text}, {'arguments': []})


def test_nullable_unused_attributes_are_accepted_but_wrong_family_values_are_not():
    from src.schemas import validate_output
    from src.discourse_classification.roles import extraction_schema, validate_extraction
    text = 'Natural products are good.'
    a = argument('SOURCE_JUSTIFICATION', [ref('Natural', 'BASIS'), ref('good', 'CLAIM')], basis='NATURE', progression=None)
    validate_output({'arguments': [a]}, extraction_schema())
    validate_extraction(build_graph(text), {'comment': text}, {'arguments': [a]})
    a['progression'] = 'ADVERSE'
    with pytest.raises(ValueError, match='attribute'):
        validate_extraction(build_graph(text), {'comment': text}, {'arguments': [a]})


def test_functional_risk_and_protection_do_not_invent_issue_comparison():
    text = 'Workers are attacked. Who will maintain public services? We must protect workers for everyone.'
    a = argument('CONSEQUENCE', [ref('Workers are attacked', 'ACTION'),
        ref('Who will maintain public services?', 'OUTCOME'), ref('We must protect workers for everyone', 'CLAIM')],
        progression='ADVERSE')
    cs = match(text, [a])
    assert {c['label'] for c in cs} == {'Slippery Slope'}
    winner = select_candidate(cs)
    assert winner['label'] == 'Slippery Slope'
    assert 'projection' not in winner


@pytest.mark.parametrize('collective,claim', [
    (False, True), (True, False), (True, True),
])
def test_causal_warning_is_not_a_comparison_regardless_of_protection_scope(collective, claim):
    outcome = 'public services stop' if collective else 'one private task stops'
    text = f'Workers are attacked. {outcome}. We must protect workers.'
    evidence = [ref('Workers are attacked', 'ACTION'), ref(outcome, 'OUTCOME')]
    if claim:
        evidence.append(ref('We must protect workers', 'CLAIM'))
    a = argument('CONSEQUENCE', evidence, progression='ADVERSE')
    assert {c['label'] for c in match(text, [a])} == {'Slippery Slope'}


def test_reported_acceptance_missing_from_roles_is_a_completion_focus():
    from src.discourse_classification.roles import uncovered_claims
    text = 'It is unfortunate that people will accept what has always been done.'
    assert uncovered_claims(build_graph(text), [])


def test_hypothetical_acceptance_does_not_trigger_conclusion_completion():
    from src.discourse_classification.roles import uncovered_claims
    text = 'Will we jail people? After that seems accepted, will we execute them?'
    assert uncovered_claims(build_graph(text), []) == []


@pytest.mark.parametrize('with_step', [True, False])
def test_explicit_event_chain_cannot_be_projected_into_priority(with_step):
    text = 'Teachers are attacked. Then education fails. Public literacy is lost. We should protect teachers for everyone.'
    evidence = [ref('Teachers are attacked', 'ACTION'), ref('Public literacy is lost', 'OUTCOME'),
                ref('We should protect teachers for everyone', 'CLAIM')]
    if with_step:
        evidence.append(ref('Then education fails', 'STEP'))
    a = argument('CONSEQUENCE', evidence, progression='ADVERSE')
    assert {c['label'] for c in match(text, [a])} == {'Slippery Slope'}


@pytest.mark.parametrize('error_type', [ValueError, RuntimeError, OSError])
def test_optional_completion_failure_preserves_primary_decision_and_evidence(error_type):
    class FailingCompletion(RoleClient):
        def generate(self, **kwargs):
            if kwargs['metadata']['stage'] == 'discourse_argument_completion':
                raise error_type('Optional completion failed')
            return super().generate(**kwargs)
    a = argument('CONSEQUENCE', [ref('ban meetings', 'ACTION'), ref('silence debate', 'OUTCOME')], progression='ADVERSE')
    text = 'They ban meetings and silence debate. We must protect public access.'
    result = classify(FailingCompletion([a]), {'comment': text}, '1', method='rules')
    assert result['label'] == 'Slippery Slope'
    assert result['candidates'] and result['graph'] and result['evidence']
    assert result['role_completion_status'] == 'failed'
    assert result['calls'] == 2


def test_role_schema_requires_the_selected_family_attribute():
    from src.schemas import validate_output
    from src.discourse_classification.roles import extraction_schema
    a = argument('SOURCE_JUSTIFICATION', [ref('Natural', 'BASIS'), ref('good', 'CLAIM')])
    with pytest.raises(ValueError):
        validate_output({'arguments': [a]}, extraction_schema())


def test_equal_support_for_different_labels_is_explicitly_ambiguous():
    cs = [{'label': 'Slippery Slope', 'support': [2, 1, 1]},
          {'label': 'Hasty Generalization', 'support': [2, 1, 1]}]
    assert select_candidate(cs) is None


def test_explicit_priority_comparison_is_a_complete_pattern():
    text = 'One missing report matters less than institutional censorship. We must protect public access.'
    a = argument('ISSUE_COMPARISON', [ref('One missing report', 'FOCAL_ISSUE'),
        ref('institutional censorship', 'COMPARISON_ISSUE'), ref('We must protect public access', 'CLAIM')],
        use='PRIORITIZE', severity='HIGHER')
    assert match(text, [a])[0]['support'][0] == 2


def test_broader_issue_priority_matches_without_claiming_higher_severity():
    text = 'One broken service. Loss of public access. We should protect access for everyone.'
    a = argument('ISSUE_COMPARISON', [ref('One broken service', 'FOCAL_ISSUE'),
        ref('Loss of public access', 'COMPARISON_ISSUE'), ref('We should protect access for everyone', 'CLAIM')],
        use='PRIORITIZE', severity='BROADER')
    assert match(text, [a])[0]['label'] == 'Appeal to Worse Problems'


def test_uncovered_conclusion_triggers_one_bounded_role_completion():
    a = argument('CONSEQUENCE', [ref('Ignore one complaint', 'ACTION'), ref('further complaints', 'OUTCOME')], progression='ORDINARY')
    b = argument('ISSUE_COMPARISON', [ref('one complaint', 'FOCAL_ISSUE'),
        ref('institutional censorship', 'COMPARISON_ISSUE'), ref('We must protect public access', 'CLAIM')],
        use='PRIORITIZE', severity='HIGHER')

    class CompletionClient(RoleClient):
        def generate(self, **kwargs):
            stage = kwargs['metadata']['stage']
            if stage == 'discourse_argument_completion':
                payload = json.loads(kwargs['user_prompt'])
                assert payload['focus_nodes']
                assert 'definitions' not in payload and 'candidates' not in payload
                self.arguments = [b]
            return super().generate(**kwargs)

    client = CompletionClient([a])
    text = 'Ignore one complaint and expect further complaints. But institutional censorship prevents public access. We must protect public access.'
    result = classify(client, {'comment': text}, '1', method='rules')
    assert result['label'] == 'Appeal to Worse Problems'
    assert result['calls'] == 2
    assert [s for s, _ in client.calls] == ['discourse_argument_roles', 'discourse_argument_completion']


class RoleClient:
    def __init__(self, arguments):
        self.arguments = arguments
        self.calls = []

    def generate(self, **kwargs):
        from src.llm.client import validate_output
        payload = json.loads(kwargs['user_prompt'])
        self.calls.append((kwargs['metadata']['stage'], payload))
        if kwargs['metadata']['stage'] == 'discourse_direct':
            assert set(payload) == {'sources', 'definitions'}
            output = {'label': 'Appeal to Nature', 'reason': 'Naturalness used as value.',
                      'evidence': [{'source': 'comment', 'text': 'Natural'}]}
        else:
            assert 'definitions' not in payload and 'candidates' not in payload
            output = {'arguments': self.arguments}
        validate_output(output, kwargs['schema'])
        kwargs['validator'](output)
        return SimpleNamespace(output=output)


def test_primary_pipeline_matches_roles_in_one_call_without_verifier_or_recovery():
    a = argument('SOURCE_JUSTIFICATION', [ref('Natural', 'BASIS'), ref('good', 'CLAIM')], basis='NATURE')
    client = RoleClient([a])
    result = classify(client, {'comment': 'Natural products are good.'}, '1', implicit=True)
    assert result['label'] == 'Appeal to Nature'
    assert result['primary_prediction'] == result['label']
    assert result['calls'] == 1
    assert [stage for stage, _ in client.calls] == ['discourse_argument_roles']


def test_clean_direct_baseline_never_calls_parser_or_supplies_graph():
    def fail(_):
        raise AssertionError('Direct baseline cannot invoke parser')
    client = RoleClient([])
    assert classify(client, {'comment': 'Natural products are good.'}, '1', method='direct', parser=fail)['label'] == 'Appeal to Nature'


def test_unresolved_is_not_api_failure_and_is_skipped_on_resume(tmp_path):
    data = tmp_path / 'input.json'
    data.write_text(json.dumps([{'id': '1', 'comment': 'Natural products are good.', 'gold': 'Appeal to Nature'}]))
    config = {'input': str(data), 'model': {}, 'method': 'rules', 'parser': 'rules',
              'context': 'comment_only', 'output_root': str(tmp_path / 'runs')}
    client = RoleClient([])
    metrics = execute(config, output='test', client=client)
    assert metrics['errors'] == 0 and metrics['unresolved'] == 1
    assert metrics['accuracy_all_selected'] == 0
    execute(config, output='test', client=client, resume=True)
    assert len(client.calls) == 1


def test_runner_excludes_entire_evaluation_article_set_before_limit(tmp_path, monkeypatch):
    import src.discourse_classification.runner as runner
    data = tmp_path / 'input.json'
    data.write_text(json.dumps([
        {'id': '1', 'article_id': 327, 'comment': 'Natural products are good.', 'gold': 'Appeal to Nature'},
        {'id': '2', 'article_id': 449, 'comment': 'Natural products are good.', 'gold': 'Appeal to Nature'},
    ]))
    def capture(client, sources, sample_id, **kwargs):
        assert kwargs['demo_exclusions'] == {327, 449}
        return {'label': 'Appeal to Nature', 'decision_mode': 'role_match', 'candidates': []}
    monkeypatch.setattr(runner, 'classify', capture)
    config = {'input': str(data), 'model': {}, 'method': 'rules', 'parser': 'rules', 'output_root': str(tmp_path / 'runs')}
    assert execute(config, output='demo', limit=1, client=RoleClient([]))['ok'] == 1


def test_coverage_and_accuracy_include_unresolved_samples():
    rows = [{'sample_id': '1', 'task': 'classification', 'status': 'ok', 'gold': 'Appeal to Nature',
             'prediction': 'Appeal to Nature', 'primary_prediction': 'Appeal to Nature', 'candidates': [{'label': 'Appeal to Nature'}]},
            {'sample_id': '2', 'task': 'classification', 'status': 'unresolved', 'gold': 'Appeal to Nature',
             'prediction': None, 'candidates': []}]
    metrics = summarize(rows, False, 'graph')
    assert metrics['coverage']['Appeal to Nature']['recall'] == .5
    assert metrics['accuracy_all_selected'] == .5
    assert metrics['completion_rate'] == .5


def test_optional_fallback_does_not_contaminate_primary_coverage():
    rows = [{'sample_id': '1', 'task': 'classification', 'status': 'ok', 'gold': 'Appeal to Nature',
             'prediction': 'Appeal to Nature', 'primary_prediction': None, 'primary_candidates': [],
             'decision_mode': 'recovery_legacy', 'candidates': [{'label': 'Appeal to Nature'}]}]
    metrics = summarize(rows, False, 'graph')
    assert metrics['coverage']['Appeal to Nature']['recall'] == 0
    assert metrics['primary_decisions'] == 0
    assert metrics['recovery_count'] == 1
