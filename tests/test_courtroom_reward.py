from copy import deepcopy
import json

import numpy as np
import pytest

from src.courtroom_rl.reward import RewardConfig, RewardEngine
from src.courtroom_rl.env import CourtroomEnv, Budget
from src.courtroom_rl.executor import FixtureExecutor
from src.courtroom_rl.observation import encode
from src.data.loader import ModelInput
from src.labels import FALLACIES


GOLD = 'Appeal to Tradition'
WRONG = 'False Dilemma'
CASE = ModelInput('Title', 'Parent', 'Old practice. Therefore this is the best practice.')


class FixedAssessor:
    fingerprint = 'fixed-test-assessor'
    def __init__(self,p=.4):
        self.p = p
        self.inputs = []
    def probabilities(self,state):
        self.inputs.append(deepcopy(state))
        values = np.full(8,(1-self.p)/7)
        values[FALLACIES.index(GOLD)] = self.p
        return values


def env(mode='crew',**kwargs):
    e = CourtroomEnv(FixtureExecutor(),mode=mode,assessor=kwargs.pop('assessor',FixedAssessor()),**kwargs)
    e.reset(CASE,gold=GOLD,sample_id='sample')
    return e


def test_crew_wrong_charge_has_no_confidence_or_grounding_bonus():
    e = env()
    e.step('ACCUSE',WRONG)
    d = e.trace[-1]['reward_diagnostics']
    assert d['delta_local'] == d['delta_board'] == d['delta_decision'] == 0
    assert e.trace[-1]['rewards']['shaping'] == 0


def test_wrong_charge_positive_assessor_gain_is_suppressed():
    assessor = FixedAssessor(.01)
    e = env(assessor=assessor)
    assessor.p = .99
    e.step('ACCUSE',WRONG)
    d = e.trace[-1]['reward_diagnostics']
    assert d['delta_decision'] > 0
    assert d['wrong_charge_gain_suppressed']
    assert e.trace[-1]['rewards']['shaping'] == 0


def test_new_source_evidence_can_produce_negative_decision_delta():
    assessor = FixedAssessor(.99)
    e = env(assessor=assessor)
    assessor.p = .01
    e.step('ACCUSE',WRONG)
    assert e.trace[-1]['reward_diagnostics']['delta_decision'] < 0
    assert e.trace[-1]['rewards']['shaping'] < 0


def test_local_evidence_subsets_and_recombinations_do_not_pay_again():
    from src.courtroom_rl.evidence import passages_for, resolve_references
    e = env()
    passages = passages_for(CASE)
    event = {'role':'Prosecutor','action':'ACCUSE','target':GOLD,'invalid':False,
             'payload':resolve_references({'label':GOLD,'evidence_ids':['T1','T2']},passages)}
    e.reward_engine._update_local(e.state,event)
    units = set(e.reward_engine.local_units['Prosecutor'])
    for ids in (['T1'],['T2'],['T2','T1']):
        event['payload'] = resolve_references({'label':GOLD,'evidence_ids':ids},passages)
        e.reward_engine._update_local(e.state,event)
        assert e.reward_engine.local_units['Prosecutor'] == units


def test_grounded_dispute_of_wrong_charge_improves_local_and_board():
    e = env()
    e.step('ACCUSE',WRONG)
    _,r,*_ = e.step('CHALLENGE','C1')
    d = e.trace[-1]['reward_diagnostics']
    assert d['delta_local'] > 0 and d['delta_board'] > 0
    assert r > 0


def test_routing_rest_and_concession_receive_no_component_bonus():
    for defense_action in ('CONCEDE','REST_DEFENSE'):
        e = env()
        e.step('ACCUSE',GOLD)
        e.step(defense_action,'C1' if defense_action=='CONCEDE' else None)
        assert e.trace[-1]['rewards']['shaping'] == 0
    e = env()
    e.step('ACCUSE',WRONG)
    e.step('CHALLENGE','C1')
    e.step('REQUEST_PROSECUTOR','C1')
    d = e.trace[-1]['reward_diagnostics']
    assert d['delta_local'] == d['delta_board'] == d['delta_decision'] == 0


def test_persistent_local_and_identical_state_do_not_pay_twice():
    e = env()
    e.step('ACCUSE',GOLD)
    state = deepcopy(e.state)
    event = {'role':'Prosecutor','action':'ACCUSE','target':GOLD,
             'payload':e.trace[0]['payload'],'invalid':False,'budget_blocked':False}
    rewards,diagnostics = e.reward_engine.transition(state,event,0,0,0)
    assert diagnostics['delta_local'] == diagnostics['delta_board'] == diagnostics['delta_decision'] == 0
    assert rewards['shaping'] == 0


def test_terminal_is_once_and_progress_cannot_swamp_it():
    e = env(progress_scale=100,episode_progress_cap=.5)
    e.step('ACCUSE',GOLD)
    e.step('REST_DEFENSE',None)
    e.step('VERDICT',GOLD)
    assert sum(abs(t['rewards']['shaping']) for t in e.trace) <= .5
    assert [t['rewards']['terminal'] for t in e.trace] == [0,0,1]
    assert e.trace[-1]['reward_diagnostics']['delta_decision'] == 0


def test_crew_formula_weight_ramp_and_output_token_cost():
    e = env()
    e.step('ACCUSE',GOLD)
    d = e.trace[-1]['reward_diagnostics']
    assert d['w_t'] == pytest.approx(.2)
    expected=.3*((1-.2)*(.4*d['delta_local']+.6*d['delta_board'])+.2*d['delta_decision'])
    assert e.trace[-1]['rewards']['shaping'] == pytest.approx(expected)
    assert e.trace[-1]['rewards']['token_cost'] == pytest.approx(-25e-5)


def test_potential_telescopes_with_zero_terminal_potential():
    e = env(mode='potential',gamma=.99)
    initial = e.reward_engine.potential
    e.step('ACCUSE',GOLD)
    e.step('REST_DEFENSE',None)
    e.step('VERDICT',GOLD)
    shaped = sum(.99**t*x['rewards']['shaping'] for t,x in enumerate(e.trace))
    assert shaped == pytest.approx(-initial)
    assert e.reward_engine.potential == 0


def test_reward_gold_and_scores_do_not_enter_public_observation_or_assessor():
    assessor = FixedAssessor()
    a,b = env(assessor=assessor),env()
    b._gold = WRONG
    b.reward_engine.reset(b.state,WRONG)
    a.step('ACCUSE',GOLD)
    b.step('ACCUSE',GOLD)
    assert a.public_state() == b.public_state()
    assert (encode(a)==encode(b)).all()
    for state in assessor.inputs:
        from dataclasses import asdict
        serialized=json.dumps(asdict(state))
        assert 'reward_diagnostics' not in serialized and 'gold' not in serialized


def test_nonterminal_no_gold_does_not_call_assessor():
    e = CourtroomEnv(FixtureExecutor(),mode='crew')
    e.reset(CASE)
    e.step('ACCUSE',GOLD)
    assert e.trace[-1]['rewards']['shaping'] == 0


def test_reward_configuration_rejects_unbounded_or_invalid_scales():
    with pytest.raises(ValueError):RewardConfig(local_scale=0)
    with pytest.raises(ValueError):RewardConfig(episode_progress_cap=1.1)
    with pytest.raises(ValueError):RewardConfig(mode='raw_confidence')
