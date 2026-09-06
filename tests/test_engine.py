import copy
import json

import pytest

from src.data.loader import ModelInput
from src.engine import Engine
from src.labels import ROLES
from src.schemas import validate_plan


def report(label='Fallacious', confidence=0.9):
    return {'prediction': label, 'confidence': confidence, 'content': 'Text supports this assessment.'}


class ScriptedLLM:
    """Records the actual model boundary; no labels enter through this interface."""
    def __init__(self, protocol='round_robin', disagree=False):
        self.protocol = protocol
        self.calls = []
        self.disagree = disagree

    def generate(self, *, system_prompt, user_prompt, schema, metadata, validator=None):
        payload = json.loads(user_prompt)
        self.calls.append((metadata.copy(), payload, system_prompt))
        if metadata['role'] == 'Planner':
            result = {'protocol': self.protocol, 'topic': 'Assess the inference.', 'reason': 'Resolve disagreement.',
                      'order': list(ROLES), 'affirmative': ['Factual'], 'negative': ['Logical', 'Contextual'],
                      'examiner': 'Logical', 'max_rounds': 3}
        elif metadata['stage'].endswith('question') or metadata['stage'].endswith('reflection'):
            result = {'question': 'Which premise supports the conclusion?', 'content': 'Check the gap.'}
            if metadata['stage'].endswith('reflection'):
                result['question'] = None
        else:
            label = schema['properties']['prediction']['enum'][-1]
            if self.disagree and metadata['role'] == 'Factual':
                label = schema['properties']['prediction']['enum'][0]
            result = report(label)
        if validator:
            validator(result)
        return result


def run(protocol='round_robin', mode='fixed', disagree=False, task='detection'):
    llm = ScriptedLLM(protocol, disagree)
    engine = Engine(llm, task=task, mode=mode, protocol=protocol, max_rounds=3)
    result = engine.run(ModelInput('TITLE', 'PARENT', 'TARGET'), {'sample_id': '42:2'})
    return result, llm


def test_planner_runs_after_independent_reports_and_cannot_see_gold():
    result, llm = run(mode='adaptive')
    assert [c[0]['role'] for c in llm.calls[:4]] == ['Factual', 'Logical', 'Contextual', 'Planner']
    assert all(not c[1]['reports'] for c in llm.calls[:3])
    assert set(llm.calls[3][1]['reports']) == set(ROLES)
    assert result['prediction'] == 'Fallacious'
    for _, payload, _ in llm.calls:
        assert payload['input'] == {'title': 'TITLE', 'parent_comment': 'PARENT', 'comment': 'TARGET'}
        assert 'gold' not in payload


def test_round_robin_sequential_replies_see_previous_speaker():
    result, llm = run()
    turns = [c for c in llm.calls if c[0]['stage'].startswith('rr_')]
    assert [c[0]['role'] for c in turns[:3]] == ['Factual', 'Logical', 'Contextual']
    assert len(turns[0][1]['history']) == 0
    assert turns[1][1]['history'][-1]['role'] == 'Factual'
    assert result['stop_reason'] == 'consensus'
    assert len(result['deliberation']) == 6  # At least two complete rounds.


def test_point_counterpoint_participates_in_disjoint_teams():
    result, llm = run('point_counterpoint', disagree=True)
    turns = result['deliberation']
    assert {t['role'] for t in turns} == set(ROLES)
    assert {t['role'] for t in turns if t['side'] == 'affirmative'} == {'Factual'}
    assert {t['role'] for t in turns if t['side'] == 'negative'} == {'Logical', 'Contextual'}
    assert result['stop_reason'] == 'stagnation'


def test_cross_examination_answers_question_and_reflects():
    result, llm = run('cross_examination', mode='adaptive')
    assert result['stop_reason'] == 'information_saturation'
    assert [t['kind'] for t in result['deliberation']] == ['question', 'answer', 'answer', 'reflection']
    answers = [c for c in llm.calls if c[0]['stage'].startswith('ce_answer')]
    assert {c[0]['role'] for c in answers} == {'Factual', 'Contextual'}
    assert all(c[1]['question'] == 'Which premise supports the conclusion?' for c in answers)


@pytest.mark.parametrize('mode,expected', [('single', 1), ('no_deliberation', 4)])
def test_ablations_skip_unnecessary_calls(mode, expected):
    result, llm = run(mode=mode, task='classification')
    assert len(llm.calls) == expected
    assert result['prediction'] == 'Slippery Slope'
    assert all('known to contain a logical fallacy' in c[2] for c in llm.calls)


def test_plan_rejects_absent_or_duplicate_participants():
    _, llm = run(mode='adaptive')
    plan = {'protocol': 'point_counterpoint', 'topic': 'x', 'reason': 'x',
            'order': list(ROLES), 'affirmative': ['Factual'], 'negative': ['Factual', 'Logical'],
            'examiner': 'Logical', 'max_rounds': 3}
    with pytest.raises(ValueError):
        validate_plan(plan, 3)
    plan.update(negative=['Logical', 'Contextual'], max_rounds=6)
    with pytest.raises(ValueError):
        validate_plan(plan, 3)


@pytest.mark.parametrize('task', ['detection', 'classification'])
@pytest.mark.parametrize('protocol,turns', [('round_robin', 9), ('point_counterpoint', 9), ('cross_examination', 12)])
def test_disabled_early_stop_exhausts_protocol_budget(task, protocol, turns):
    llm = ScriptedLLM(protocol)
    engine = Engine(llm, task=task, mode='fixed', protocol=protocol, max_rounds=3, early_stop=False)
    result = engine.run(ModelInput('T', '', 'C'), {'sample_id': 'budget'})
    assert result['stop_reason'] == 'max_rounds'
    assert len(result['deliberation']) == turns
    assert {t['role'] for t in result['deliberation']} == set(ROLES)


def test_engine_rejects_labeled_dictionary_at_boundary():
    engine = Engine(ScriptedLLM(), task='detection')
    with pytest.raises(TypeError):
        engine.run({'comment': 'C', 'gold': 'Fallacious'}, {})


def test_adaptive_point_counterpoint_requires_natural_two_sided_reports():
    plan = {'protocol': 'point_counterpoint', 'topic': 'x', 'reason': 'x',
            'order': list(ROLES), 'affirmative': ['Factual'], 'negative': ['Logical', 'Contextual'],
            'examiner': 'Logical', 'max_rounds': 3}
    initial = {role: report() for role in ROLES}
    with pytest.raises(ValueError, match='two'):
        validate_plan(plan, 3, initial)
    initial['Factual'] = report('Non-Fallacious')
    validate_plan(plan, 3, initial)
    plan.update(affirmative=['Logical'], negative=['Factual', 'Contextual'])
    with pytest.raises(ValueError, match='teams'):
        validate_plan(plan, 3, initial)
