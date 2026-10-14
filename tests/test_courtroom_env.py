import json

import pytest

from src.data.loader import ModelInput
from src.courtroom_rl.env import CourtroomEnv, Budget
from src.courtroom_rl.executor import FixtureExecutor
from src.courtroom_rl.replay import replay


TEXT = "We've always done it this way, so it must be the best way."
LABEL = 'Appeal to Tradition'


def environment(**kwargs):
    env = CourtroomEnv(FixtureExecutor(), budget=Budget(**kwargs))
    env.reset(ModelInput('Title', '', TEXT), gold=LABEL, sample_id='fixture')
    return env


def accuse(env):
    env.step('ACCUSE', LABEL)


def test_initial_defense_opportunity_and_gold_is_private():
    env = environment()
    assert env.legal_actions() == {'ACCUSE': list(env.labels)}
    assert 'gold' not in json.dumps(env.public_state())
    accuse(env)
    assert env.state.active_role == 'Defender'
    assert 'VERDICT' not in env.legal_actions()
    env.step('REST_DEFENSE', None)
    assert env.state.active_role == 'Judge'
    assert not env.state.done
    assert env.state.claims[0].status == 'OPEN'
    _, reward, done, _, info = env.step('VERDICT', LABEL)
    assert done and reward > .9
    assert info['rewards']['terminal'] == 1
    with pytest.raises(ValueError):
        env.step('VERDICT', LABEL)


def test_targeted_request_response_and_exhausted_request():
    env = environment()
    accuse(env)
    env.step('CHALLENGE', 'C1')
    assert env.state.claims[0].status == 'DISPUTED'
    env.step('REQUEST_PROSECUTOR', 'C1')
    assert env.state.pending_request == ('Prosecutor', 'C1')
    assert 'ACCUSE' not in env.legal_actions()
    env.step('DEFEND_CLAIM', 'C1')
    assert env.state.active_role == 'Judge'
    assert env.state.pending_request is None
    assert env.state.claims[0].response_count == 1
    assert 'REQUEST_PROSECUTOR' not in env.legal_actions()
    assert 'REQUEST_DEFENDER' not in env.legal_actions()


def test_concede_is_local_and_rest_does_not_end_case():
    env = environment()
    accuse(env)
    env.step('CONCEDE', 'C1')
    assert env.state.claims[0].status == 'CONCEDED'
    assert not env.state.done
    assert env.legal_actions() == {'VERDICT': list(env.labels)}


def test_budget_forces_scored_verdict_without_dropping_case():
    env = environment(max_decisions=1)
    accuse(env)
    assert env.legal_actions() == {'VERDICT': list(env.labels)}
    env.step('VERDICT', LABEL)
    assert env.state.done and env.state.forced_verdict
    assert env.state.final_label == LABEL
    assert env.trace[-1]['rewards']['terminal'] == 1
    assert env.trace[-1]['forced_verdict']


def test_illegal_action_cannot_mutate_state():
    env = environment()
    before = env.public_state()
    with pytest.raises(ValueError):
        env.step('VERDICT', LABEL)
    assert env.public_state() == before


def test_revision_and_alternative_do_not_cycle():
    env = environment(max_decisions=12)
    accuse(env)
    env.step('PROPOSE_ALTERNATIVE', 'False Dilemma')
    assert len(env.state.claims) == 2
    env.step('REQUEST_PROSECUTOR', 'C2')
    assert LABEL not in env.legal_actions().get('REVISE_CHARGE', [])
    env.step('REVISE_CHARGE', 'False Dilemma')
    assert env.state.charge_label == 'False Dilemma'
    assert len(env.state.claims) == 3
    assert env.state.pending_request is None


def test_replay_reconstructs_normalized_state():
    env = environment()
    accuse(env)
    env.step('CHALLENGE', 'C1')
    env.step('REQUEST_PROSECUTOR', 'C1')
    env.step('DEFEND_CLAIM', 'C1')
    env.step('VERDICT', LABEL)
    restored = replay(ModelInput('Title', '', TEXT), env.trace, Budget())
    assert restored.public_state() == env.public_state()


def test_invented_quote_is_rejected_before_ledger_update():
    class BadExecutor(FixtureExecutor):
        def execute(self, *args):
            out = super().execute(*args)
            out.payload['supported_quote'] = 'invented evidence'
            return out
    env = CourtroomEnv(BadExecutor())
    env.reset(ModelInput('', '', TEXT), gold=LABEL)
    with pytest.raises(ValueError, match='quote'):
        accuse(env)
    assert not env.state.claims


def test_observation_identifies_claims_without_gold():
    from src.courtroom_rl.observation import encode
    env = environment()
    accuse(env)
    first = encode(env)
    env.state.claims[0].proposition = 'A different reasoning mechanism'
    second = encode(env)
    assert first.shape == second.shape
    assert (first != second).any()
    env._gold = 'False Dilemma'
    assert (second == encode(env)).all()


def test_judge_observes_substantive_replies():
    from src.courtroom_rl.observation import encode
    env = environment()
    accuse(env)
    env.step('CHALLENGE', 'C1')
    first = encode(env)
    env.state.argument_events[-1]['payload']['mechanism'] = 'The charge is unsupported because longevity is merely descriptive.'
    assert (first != encode(env)).any()


def test_budget_blocked_trace_replays():
    from src.courtroom_rl.executor import BudgetExhausted
    class Blocked(FixtureExecutor):
        def execute(self,*args):
            raise BudgetExhausted('Preflight blocked')
    env = CourtroomEnv(Blocked())
    env.reset(ModelInput('', '', TEXT), gold=LABEL)
    accuse(env)
    env.step('VERDICT', LABEL)
    assert replay(ModelInput('', '', TEXT),env.trace,Budget()).public_state() == env.public_state()


def test_similar_claims_with_negation_are_flagged_not_rejected():
    from src.courtroom_rl.ledger import insert_claim
    env = environment()
    first = {'label':LABEL,'supported_quote':TEXT,'source':'comment',
             'mechanism':'The historical practice is sufficient justification for the conclusion because it is old.'}
    second = {**first,'mechanism':'The historical practice is not sufficient justification for the conclusion because it is old.'}
    insert_claim(env.state,'ACCUSE',first)
    inserted = insert_claim(env.state,'ACCUSE',second)
    assert len(env.state.claims) == 2
    assert inserted.similarity_review_candidates == ['C1']


def test_revision_cannot_only_relabel_the_same_reasoning():
    from src.courtroom_rl.ledger import validate_payload
    env = environment()
    accuse(env)
    old = env.state.claims[0]
    payload = {'label':'False Dilemma','supported_quote':old.source_span['quote'],
               'source':'comment','mechanism':old.proposition,'attacks_claim_ids':[],
               'answer_to_pending_request':''}
    with pytest.raises(ValueError,match='new grounded distinction'):
        validate_payload(payload,env.state,'REVISE_CHARGE','False Dilemma')
