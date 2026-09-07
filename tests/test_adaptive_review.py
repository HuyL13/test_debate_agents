import json

import pytest

from src.data.loader import ModelInput
from src.engine import Engine
from src.labels import ROLES
from src.schemas import validate_output


class ReviewLLM:
    def __init__(self, disagree):
        self.disagree = disagree
        self.calls = []

    def generate(self, *, user_prompt, schema, metadata, validator=None, **kwargs):
        payload = json.loads(user_prompt)
        self.calls.append((metadata, payload))
        assert metadata['role'] != 'Planner'
        label = 'Non-Fallacious' if self.disagree and metadata['role'] == 'Factual' else 'Fallacious'
        value = {'prediction': label, 'confidence': 0.8, 'content': 'Interpret the supplied claim.'}
        if 'supporting_quote' in schema['properties']:
            value['supporting_quote'] = 'target claim'
        validate_output(value, schema)
        if validator:
            validator(value)
        return value


def test_unanimous_reports_skip_planner_and_review_but_keep_arbiter():
    llm = ReviewLLM(False)
    result = Engine(llm, task='detection', adaptive_policy='disagreement').run(
        ModelInput('title', '', 'target claim'), {})
    assert len(llm.calls) == 4
    assert llm.calls[-1][0]['role'] == 'Arbiter'
    assert result['stop_reason'] == 'initial_consensus'
    assert result['deliberation'] == []


def test_disagreement_uses_one_independent_review_per_role():
    llm = ReviewLLM(True)
    result = Engine(llm, task='detection', adaptive_policy='disagreement').run(
        ModelInput('title', '', 'target claim'), {})
    assert len(llm.calls) == 7
    reviews = [p for m, p in llm.calls if m['stage'] == 'independent_review']
    assert len(reviews) == 3
    assert all(p['reports'] == result['initial_agents'] and p['history'] == [] for p in reviews)
    assert {x['role'] for x in result['deliberation']} == set(ROLES)
    assert all('supporting_quote' in x for x in result['deliberation'])
    assert result['stop_reason'] == 'one_review_round'


def test_review_quote_must_occur_in_target():
    from src.schemas import validate_review_quote
    validate_review_quote({'supporting_quote': 'target  claim'}, 'The target claim is here.')
    for quote in ('', '  ', 'invented evidence', 'title only'):
        with pytest.raises(ValueError):
            validate_review_quote({'supporting_quote': quote}, 'The target claim is here.')


def test_arbiter_can_reject_unanimous_initial_label():
    class ContrarianArbiter(ReviewLLM):
        def generate(self, **kwargs):
            value = super().generate(**kwargs)
            if kwargs['metadata']['role'] == 'Arbiter':
                value['prediction'] = 'Non-Fallacious'
            return value

    llm = ContrarianArbiter(False)
    result = Engine(llm, task='detection', adaptive_policy='disagreement').run(
        ModelInput('title', '', 'target claim'), {})
    assert all(r['prediction'] == 'Fallacious' for r in result['initial_agents'].values())
    assert result['prediction'] == 'Non-Fallacious'
