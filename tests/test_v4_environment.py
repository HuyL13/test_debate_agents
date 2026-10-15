from copy import deepcopy
import numpy as np
import pytest
from dataclasses import asdict
from src.data.loader import ModelInput
from src.labels import FALLACIES
from src.courtroom_rl.action_centric.embeddings import FixtureEncoder
from src.courtroom_rl.action_centric_v4.env import CourtroomEnv
from src.courtroom_rl.action_centric_v4.executor import FixtureExecutor, contract, dialogue_view
from src.courtroom_rl.action_centric_v4.observation import encode
from src.courtroom_rl.action_centric_v4.replay import replay


def environment(executor=None):
    e=CourtroomEnv(executor or FixtureExecutor(),text_encoder=FixtureEncoder())
    e.reset(ModelInput('Title','Parent','Old practice. Therefore it is the best.'),gold=FALLACIES[-1],sample_id='s')
    return e


def test_target_is_actor_selected_and_invalid_target_is_free():
    e=environment(); calls=e.state.calls
    with pytest.raises(ValueError,match='target'):e.step('CHALLENGE','C999')
    assert e.state.calls==calls and not e.trace
    e.step('CHALLENGE','C2')
    assert e.trace[-1]['actor_target']=='C2' and e.trace[-1]['target']=='C2'
    assert e.state.claims[1].status=='DISPUTED'


def test_requests_bind_recipient_and_singleton_schema():
    e=environment();e.step('CHALLENGE','C2');e.step('REQUEST_SUPPORT','C2')
    assert e.legal_targets('SUPPORT')==['C2']
    assert e.state.pending_request['eligible_claim_ids']==['C2']
    e.state.actor_target='C2'
    schema,_=contract(e.state,'SUPPORT',e.budget)
    assert schema['properties']['claim_id']['enum']==['C2']
    e.step('SUPPORT','C2')
    assert e.state.claims[1].status=='RESPONDED'


def test_observation_contract_and_private_invariance():
    e=environment();before=encode(e)
    assert before['source'].shape==(768,)
    assert before['objects'].shape==(16,768)
    assert before['object_features'].shape==(16,34)
    assert before['history'].shape==(10,768) and before['global'].shape==(12,)
    assert before['ids'][:3]==['H1','H2','H3']
    e._gold=FALLACIES[0];e.private_probability=[1]*8
    after=encode(e)
    for key in before:
        if key!='ids':np.testing.assert_array_equal(before[key],after[key])


def test_concession_dialogue_and_terminal_reward_replay():
    e=environment();e.step('CONCEDE','C2')
    assert dialogue_view(e.state)['argument_events'][0]['payload']['reason']=='Fixture concession.'
    e.step('VERDICT')
    assert sum(t['rewards']['terminal'] for t in e.trace)==1
    assert all(t['rewards']['shaping']==0 for t in e.trace)
    row={'case_input':e.state.case_input.as_dict(),'sample_id':'s','budget':asdict(e.budget),'initialization':e.initialization,'trace':e.trace}
    r=replay(row);assert r.public_state()==e.public_state()
    bad=deepcopy(row);bad['trace'][0]['legal_targets']['CONCEDE']=['C999']
    with pytest.raises(ValueError,match='target mask'):replay(bad)

def test_executor_cannot_substitute_another_valid_target():
    class Bad(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget)
            result.payload['claim_id']='C1'
            return result
    e=environment(Bad());e.step('CHALLENGE','C2')
    assert e.trace[-1]['invalid']
    assert e.state.claims[0].status=='OPEN' and e.state.claims[1].status=='OPEN'
    assert e.trace[-1]['rewards']['invalid']==-.1


def test_history_filters_nested_runtime_and_reward_fields():
    e=environment();e.step('CONCEDE','C2');before=encode(e)
    e.state.argument_events[0]['rewards']={'gold':'SECRET'}
    e.state.argument_events[0]['payload']['private_probability']='SECRET'
    assert 'SECRET' not in str(dialogue_view(e.state))
    np.testing.assert_array_equal(before['history'],encode(e)['history'])


def test_nonfixture_128_encoder_rejected_and_no_shaping_allowed():
    class BadEncoder:
        def encode(self,texts):return np.zeros((len(texts),128))
    e=environment();e.text_encoder=BadEncoder()
    with pytest.raises(ValueError,match='768'):encode(e)
    with pytest.raises(ValueError,match='terminal'):CourtroomEnv(FixtureExecutor(),mode='crew')

def test_real_client_singleton_target_and_full_concession_prompt(tmp_path):
    import json
    from src.llm.client import Client
    from src.llm.config import ModelConfig
    from src.courtroom_rl.action_centric_v4.executor import LLMExecutor
    class Transport:
        def __init__(self):self.requests=[]
        def complete(self,payload):
            self.requests.append(deepcopy(payload))
            user=json.loads(payload['messages'][1]['content']);action=user['action_type']
            if action=='TOP3_INIT':
                obj={'hypotheses':[{'label':l,'claims':[{'evidence_ids':['T1'],'mechanism':f'Initial {i} reasoning.'}]} for i,l in enumerate(FALLACIES[:3])]}
            elif action=='CONCEDE':obj={'claim_id':'C2','reason':'Specific concession rationale.'}
            else:obj={'label':FALLACIES[-1],'evidence_ids':['T1'],'mechanism':'Independent final inference.'}
            return {'choices':[{'message':{'content':json.dumps(obj)},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':20,'completion_tokens':20,'total_tokens':40}}
    transport=Transport()
    client=Client(ModelConfig('fixture',backoff_seconds=0,max_attempts=2),tmp_path/'cache',tmp_path/'audit',transport)
    e=environment(LLMExecutor(client));e.step('CONCEDE','C2');e.step('VERDICT')
    concede=json.loads(transport.requests[-2]['messages'][1]['content'])
    assert concede['eligible_claim_ids']==['C2'] and concede['actor_target']=='C2'
    verdict=json.loads(transport.requests[-1]['messages'][1]['content'])
    assert verdict['argument_events'][0]['payload']['reason']=='Specific concession rationale.'
    material=json.dumps(transport.requests)
    assert 'gold' not in material and 'reward' not in material

def test_revised_hypothesis_author_follows_its_public_claim():
    from src.courtroom_rl.action_centric.state import Hypothesis
    e=environment()
    h=Hypothesis('H4',FALLACIES[4],None)
    e.state.hypotheses.append(h)
    claim=deepcopy(e.state.claims[0]);claim.claim_id='C4';claim.hypothesis_id='H4';claim.label=h.label
    claim.author='Prosecutor';e.state.claims.append(claim);h.claim_ids.append('C4')
    obs=encode(e)
    assert obs['object_features'][3,8]==1 and obs['object_features'][3,9]==0

def test_replay_validates_recorded_policy_masks_and_joint_logs():
    e=environment();e.step('CONCEDE','C2');e.step('VERDICT')
    row={'case_input':e.state.case_input.as_dict(),'sample_id':'s','budget':asdict(e.budget),'initialization':e.initialization,'trace':e.trace}
    first=row['trace'][0]
    first['decision']={'action':'CONCEDE','target':'C2','legal':first['legal_actions'],'targets':first['legal_targets'],
        'logprob':-.7,'action_logprob':-.5,'target_logprob':-.2}
    replay(row)
    bad=deepcopy(row);bad['trace'][0]['decision']['logprob']=0
    with pytest.raises(ValueError,match='logprob'):replay(bad)
    bad=deepcopy(row);bad['trace'][0]['decision']['targets']['CONCEDE']=['C1']
    with pytest.raises(ValueError,match='target mask'):replay(bad)

def test_declined_request_exhausts_selected_target_only():
    e=environment();e.step('CONCEDE','C3')
    e.step('REQUEST_REBUTTAL','C1');e.step('REST')
    assert 'REQUEST_REBUTTAL' in e.legal_actions()
    assert 'C1' not in e.legal_targets('REQUEST_REBUTTAL')
    assert 'C2' in e.legal_targets('REQUEST_REBUTTAL')
    e.step('REQUEST_REBUTTAL','C2')
    assert e.state.pending_request['eligible_claim_ids']==['C2']


def test_substituted_target_does_not_blacklist_unselected_claim():
    class Bad(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget);result.payload['claim_id']='C2';return result
    e=environment(Bad());e.step('CHALLENGE','C1')
    assert ['CHALLENGE','C2'] not in e.state.invalid_targets

def test_global_features_include_role_rest_and_pending_request_direction():
    e=environment();e.step('CONCEDE','C3');e.step('REQUEST_REBUTTAL','C1')
    np.testing.assert_array_equal(encode(e)['global'][-4:],[0,0,0,1])
    e.step('REST')
    assert not e.state.role_status['Defender']
    e.state.role_status['Prosecutor']=True
    np.testing.assert_array_equal(encode(e)['global'][-4:],[1,0,0,0])
