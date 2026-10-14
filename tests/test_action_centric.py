from copy import deepcopy
import numpy as np
import pytest
import torch

from src.courtroom_rl.action_centric.env import CourtroomEnv, Budget
from src.courtroom_rl.action_centric.executor import FixtureExecutor
from src.courtroom_rl.action_centric.observation import encode, ROLE_ACTIONS
from src.courtroom_rl.action_centric.trainer import PPOTrainer
from src.data.loader import ModelInput
from src.labels import FALLACIES


CASE = ModelInput('Title','Parent','Old practice. Therefore it is the best. A competing reason.')


def environment(**kwargs):
    env = CourtroomEnv(FixtureExecutor(),Budget(**kwargs))
    env.reset(CASE,gold=FALLACIES[-1],sample_id='sample')
    return env


def test_init_is_top3_llm_not_policy_transition():
    e=environment()
    assert len(e.state.hypotheses)==3
    assert len({h.label for h in e.state.hypotheses})==3
    assert 3<=len(e.state.claims)<=6
    assert e.state.active_role=='Defender' and e.state.decision_count==0
    assert e.state.calls==1 and e.trace==[]


def test_top3_duplicate_labels_rejected_atomically():
    class Bad(FixtureExecutor):
        def initialize(self,state,budget):
            result=super().initialize(state,budget)
            result.payload['hypotheses'][1]['label']=result.payload['hypotheses'][0]['label']
            return result
    e=CourtroomEnv(Bad())
    with pytest.raises(ValueError,match='distinct'):
        e.reset(CASE)
    assert not e.state.hypotheses and not e.state.claims


def test_actor_only_has_role_action_logits_and_no_target_head():
    e=environment(); t=PPOTrainer(seed=2)
    assert not hasattr(t.policies,'targets')
    for role,actions in ROLE_ACTIONS.items():
        e.state.active_role=role
        dist=t.policies.distribution(role,encode(e),e.legal_actions())
        assert dist.probs.numel()==len(actions)
        decision=t.policies.sample(role,encode(e),e.legal_actions())
        assert 'target' not in decision


def test_request_routes_to_actor_and_llm_selects_target():
    e=environment();e.step('CHALLENGE')
    assert e.trace[-1]['target']=='C1'
    e.step('REQUEST_SUPPORT')
    assert e.state.active_role=='Prosecutor'
    calls=e.state.calls
    assert e.state.pending_request['role']=='Prosecutor'
    assert 'SUPPORT' in e.legal_actions() and 'REST' in e.legal_actions()
    assert e.state.calls==calls
    e.step('SUPPORT')
    assert e.trace[-1]['target']=='C1' and e.state.active_role=='Judge'


def test_judge_llm_can_choose_outside_top3():
    e=environment();assert FALLACIES[-1] not in [h.label for h in e.state.hypotheses]
    e.step('REST');e.step('VERDICT')
    assert e.state.final_label==FALLACIES[-1]
    assert e.trace[-1]['rewards']['terminal']==1


def test_budget_forces_recorded_paid_llm_verdict():
    e=environment(max_decisions=2,max_calls=3)
    e.step('REST')
    assert e.state.forced_verdict and e.legal_actions()==['VERDICT']
    e.step('VERDICT')
    assert e.state.done and e.state.calls==2 and e.trace[-1]['forced_verdict']


def test_noop_is_logged_penalized_and_never_progress():
    from src.courtroom_rl.assessor import UniformAssessor
    e=CourtroomEnv(FixtureExecutor(),mode='crew',assessor=UniformAssessor())
    e.reset(CASE,gold=FALLACIES[-1]);e.step('REST')
    assert e.trace[-1]['rewards']['shaping']==0
    assert e.trace[-1]['rewards']['step_cost']<0


def test_gold_and_private_reward_do_not_change_observations():
    from src.courtroom_rl.assessor import UniformAssessor
    a=CourtroomEnv(FixtureExecutor(),mode='crew',assessor=UniformAssessor())
    b=CourtroomEnv(FixtureExecutor(),mode='crew',assessor=UniformAssessor())
    a.reset(CASE,gold=FALLACIES[0]);b.reset(CASE,gold=FALLACIES[-1])
    a.step('CHALLENGE');b.step('CHALLENGE')
    assert a.public_state()==b.public_state()
    assert np.array_equal(encode(a),encode(b))


def test_ippo_updates_each_role_on_global_timeline(tmp_path):
    e=environment();t=PPOTrainer(seed=2)
    trajectory=t.rollout(e,demonstration=True)
    assert {r['role'] for r in trajectory}=={'Prosecutor','Defender','Judge'}
    before={role:[p.clone() for p in actor.parameters()] for role,actor in t.policies.actors.items()}
    result=t.update([trajectory])
    for role,actor in t.policies.actors.items():
        assert any(not torch.equal(a,b) for a,b in zip(before[role],actor.parameters()))
    assert all(np.isfinite(result[k]) for k in ('actor_loss','critic_loss','entropy','approx_kl'))
    t.save(tmp_path/'checkpoint.pt',{'architecture':'action_centric_v3'})
    restored=PPOTrainer(seed=99);restored.load(tmp_path/'checkpoint.pt')
    assert all(torch.equal(a,b) for a,b in zip(t.policies.parameters(),restored.policies.parameters()))


def test_invalid_target_cannot_partially_update_ledger():
    class Bad(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget)
            if action=='CHALLENGE':result.payload['claim_id']='C999'
            return result
    e=CourtroomEnv(Bad());e.reset(CASE)
    old=deepcopy(e.state.claims);e.step('CHALLENGE')
    assert e.state.claims==old
    assert e.trace[-1]['invalid'] and e.trace[-1]['rewards']['invalid']<0
    assert e.trace[-1]['rewards']['shaping']==0


def test_top3_ungrounded_claim_rejected_before_commit():
    class Bad(FixtureExecutor):
        def initialize(self,state,budget):
            result=super().initialize(state,budget)
            result.payload['hypotheses'][2]['claims'][0]['evidence_ids']=['P1']
            return result
    e=CourtroomEnv(Bad())
    with pytest.raises(ValueError):e.reset(CASE)
    assert not e.state.claims


def test_action_feature_matrix_is_action_specific_and_neutral_unobserved():
    e=environment();v=encode(e);rows=v[:-8].reshape(4,7)
    assert np.all(rows[:,4]==.5) and np.all(rows[:,6]==0)
    assert not np.array_equal(rows[0],rows[1])
    assert 'gold' not in e.public_state() and 'reward' not in e.public_state()


def test_v3_replay_has_no_gold_or_assessor_dependency():
    from src.courtroom_rl.action_centric.replay import replay
    from src.courtroom_rl.action_centric.runner import trace_record
    from src.courtroom_rl.data import Case
    e=environment();e.step('CHALLENGE');e.step('REQUEST_SUPPORT');e.step('SUPPORT');e.step('VERDICT')
    row=trace_record(e,Case('sample',1,'train',CASE,FALLACIES[-1]))
    restored=replay(row)
    assert restored.public_state()==e.public_state()


def test_alternative_noop_does_not_add_hypothesis_and_tightens_mask():
    class Noop(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget)
            result.payload['no_op']=True;result.payload['evidence_ids']=[];result.payload['label']=None
            return result
    e=CourtroomEnv(Noop());e.reset(CASE);old=deepcopy(e.state.hypotheses)
    e.step('PROPOSE_ALTERNATIVE')
    assert e.state.hypotheses==old and e.trace[-1]['no_op']
    assert e.trace[-1]['rewards']['shaping']==0
    e.state.active_role='Defender'
    assert 'PROPOSE_ALTERNATIVE' not in e.legal_actions()


def test_role_behavior_adapter_preserves_boundaries_without_legacy_output():
    from src.courtroom_rl.action_centric.prompts import role_behavior
    assert 'BOUNDARY VERIFICATION' in role_behavior('Defender')
    assert 'DISAMBIGUATION MATRIX' in role_behavior('Judge')
    assert 'inferential link' in role_behavior('Prosecutor')
    for role in ('Prosecutor','Defender','Judge'):
        assert 'candidate_class' not in role_behavior(role)
        assert 'concede_charge' not in role_behavior(role)
        assert 'Output must include prediction' not in role_behavior(role)


def test_failed_verdict_keeps_partial_trace_and_paid_usage(tmp_path,monkeypatch):
    import json
    from src.courtroom_rl.runner import main
    original=FixtureExecutor.execute
    def fail(self,state,action,budget):
        if action=='VERDICT':raise RuntimeError('provider unavailable')
        return original(self,state,action,budget)
    monkeypatch.setattr(FixtureExecutor,'execute',fail)
    out=tmp_path/'failure'
    result=main(['smoke','--fixture','--policy','fixed-top3','--output',str(out)])
    assert result['failed']==1
    partial=json.loads((out/'partial_traces.jsonl').read_text().splitlines()[0])
    assert partial['failure_stage']=='VERDICT'
    assert partial['trace'][0]['action']=='CHALLENGE'
    prediction=json.loads((out/'predictions.jsonl').read_text())
    assert prediction['calls']>=2


def test_real_client_retries_top3_and_never_passes_gold_or_actor_label(tmp_path):
    import json
    from src.llm.client import Client
    from src.llm.config import ModelConfig
    from src.courtroom_rl.action_centric.executor import LLMExecutor
    class Transport:
        def __init__(self):self.requests=[]
        def complete(self,payload):
            self.requests.append(deepcopy(payload))
            user=json.loads(payload['messages'][1]['content'])
            action=user['action_type']
            if action=='TOP3_INIT':
                obj={'hypotheses':[{'label':l,'claims':[{'evidence_ids':['T1'],'mechanism':f'Initial {i} reasoning.'}]} for i,l in enumerate(FALLACIES[:3])]}
                if len(self.requests)==1:obj['hypotheses'][1]['label']=obj['hypotheses'][0]['label']
            elif action=='CHALLENGE':obj={'claim_id':'C2','evidence_ids':['T2'],'mechanism':'This alleged authority does not establish the conclusion.'}
            else:obj={'label':FALLACIES[-1],'evidence_ids':['T3'],'mechanism':'Independent final inference.'}
            return {'choices':[{'message':{'content':json.dumps(obj)},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':20,'completion_tokens':20,'total_tokens':40}}
    transport=Transport()
    client=Client(ModelConfig('fixture',backoff_seconds=0,max_attempts=2),tmp_path/'cache',tmp_path/'audit',transport)
    e=CourtroomEnv(LLMExecutor(client),Budget(max_tokens=100000))
    e.reset(CASE,gold=FALLACIES[-1]);assert e.state.calls==2
    e.step('CHALLENGE');assert e.trace[-1]['target']=='C2'
    e.step('VERDICT');assert e.state.final_label==FALLACIES[-1]
    material=json.dumps(transport.requests)
    assert 'gold' not in material and 'reward' not in material and 'selected_label' not in material
    assert 'claim_id' in json.loads(transport.requests[-2]['messages'][1]['content'])['required_output_fields']


def test_minimum_call_budget_reserves_actual_llm_verdict():
    e=environment(max_calls=2)
    assert e.state.forced_verdict and e.legal_actions()==['VERDICT']
    e.step('VERDICT')
    assert e.state.calls==2 and e.state.decision_count==1


def test_cached_initializer_cannot_bypass_reserved_token_budget(tmp_path,monkeypatch):
    from src.llm.client import Client,GenerationResult,CallStats
    from src.llm.config import ModelConfig
    from src.courtroom_rl.action_centric.executor import LLMExecutor
    from src.courtroom_rl.executor import BudgetExhausted
    c=Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',transport=object())
    e=environment()
    payload=e.initialization['execution']['payload']
    def cached(**kwargs):
        return GenerationResult(payload,CallStats('TOP3_INIT',1,0,True,0,16000,100,16100,0,'fixture'))
    monkeypatch.setattr(c,'generate',cached)
    with pytest.raises(BudgetExhausted):
        CourtroomEnv(LLMExecutor(c)).reset(CASE)


def test_support_for_wrong_label_cannot_get_positive_assessor_credit():
    class Assessor:
        p=.1
        def probabilities(self,state):
            v=np.full(8,(1-self.p)/7);v[-1]=self.p;return v
    class NewEvidence(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget)
            if action=='SUPPORT':result.payload['evidence_ids']=['T2']
            return result
    assessor=Assessor();e=CourtroomEnv(NewEvidence(),mode='crew',assessor=assessor)
    e.reset(CASE,gold=FALLACIES[-1]);e.step('CHALLENGE');e.step('REQUEST_SUPPORT')
    assessor.p=.9;e.step('SUPPORT')
    d=e.trace[-1]['reward_diagnostics']
    assert d['delta_decision']>0 and d['normalized_deltas']['decision']==0
    assert e.trace[-1]['rewards']['shaping']<=0


def test_duplicate_content_tightens_future_target_eligibility():
    from src.courtroom_rl.action_centric.ledger import eligible
    class Duplicate(FixtureExecutor):
        def execute(self,state,action,budget):
            result=super().execute(state,action,budget)
            if action=='CHALLENGE':result.payload['mechanism']=state.claims[0].proposition
            return result
    e=CourtroomEnv(Duplicate());e.reset(CASE);e.step('CHALLENGE')
    assert e.trace[-1]['invalid']
    assert 'C1' not in eligible(e.state,'CHALLENGE')


def test_failed_batches_do_not_trigger_extra_paid_dev_evaluations(tmp_path,monkeypatch):
    from src.courtroom_rl.runner import main
    from src.courtroom_rl.action_centric import runner
    def fail(*args):raise RuntimeError('provider unavailable')
    monkeypatch.setattr(FixtureExecutor,'initialize',fail)
    evaluations=[]
    def evaluation(*args,**kwargs):
        evaluations.append(1)
        return {'metrics':None,'coverage':0.,'top3_recall':None}
    monkeypatch.setattr(runner,'evaluate',evaluation)
    main(['train','--fixture','--limit','4','--dev-limit','1','--batch-size','2',
          '--dev-every','4','--output',str(tmp_path/'failed')])
    assert len(evaluations)==1


def test_resume_rejects_changed_ppo_batching(tmp_path):
    from src.courtroom_rl.runner import main
    main(['train','--fixture','--limit','1','--dev-limit','1','--batch-size','1','--output',str(tmp_path/'first')])
    with pytest.raises(ValueError,match='batch_size'):
        main(['train','--fixture','--limit','1','--dev-limit','1','--batch-size','2',
            '--resume',str(tmp_path/'first/last.pt'),'--output',str(tmp_path/'resume')])


@pytest.mark.parametrize('mode',['crew','terminal','potential'])
def test_reward_ablations_use_identical_generated_token_costs(mode):
    from src.courtroom_rl.assessor import UniformAssessor
    e=CourtroomEnv(FixtureExecutor(),mode=mode,assessor=UniformAssessor(),token_cost_basis='auto')
    e.reset(CASE,gold=FALLACIES[-1]);e.step('CHALLENGE')
    assert e.trace[-1]['rewards']['token_cost']==pytest.approx(-30e-5)
