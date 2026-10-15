import copy
import random
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from src.courtroom_rl.action_centric_v4.policies import RolePolicies
from src.courtroom_rl.action_centric_v4.trainer import PPOTrainer, heuristic


def observation():
    rng=np.random.default_rng(7)
    return {'source':rng.normal(size=768).astype('float32'),
      'objects':rng.normal(size=(16,768)).astype('float32'),
      'object_features':rng.normal(size=(16,34)).astype('float32'),
      'object_mask':np.array([True,True]+[False]*14), 'ids':['c1','c2']+[None]*14,
      'history':np.zeros((10,768),dtype='float32'),'history_mask':np.zeros(10,dtype=bool),
      'global':np.zeros(12,dtype='float32')}


def test_joint_probability_and_target_mask():
    torch.manual_seed(2); p=RolePolicies(); obs=observation()
    targets={'SUPPORT':['c2'],'REST':[None]}
    for _ in range(10):
        d=p.sample('Prosecutor',obs,list(targets),targets,False)
        assert d['target']==('c2' if d['action']=='SUPPORT' else None)
        lp,entropy=p.evaluate('Prosecutor',obs,list(targets),targets,d['action'],d['target'])
        assert float(lp)==pytest.approx(d['action_logprob']+d['target_logprob'])
        assert torch.isfinite(entropy)
    with pytest.raises(ValueError):p.evaluate('Prosecutor',obs,list(targets),targets,'SUPPORT','c1')
    with pytest.raises(ValueError):p.sample('Prosecutor',obs,['SUPPORT'],{'SUPPORT':['missing']},False)


def test_label_features_influence_conditional_target_and_padding_does_not():
    p=RolePolicies(); obs=observation(); targets={'SUPPORT':['c1','c2']}
    lp,_=p.evaluate('Prosecutor',obs,['SUPPORT'],targets,'SUPPORT','c1')
    changed=copy.deepcopy(obs); changed['object_features'][0,0]+=8
    other,_=p.evaluate('Prosecutor',changed,['SUPPORT'],targets,'SUPPORT','c1')
    assert not torch.allclose(lp,other)
    changed=copy.deepcopy(obs);changed['objects'][2:]=1e6;changed['object_features'][2:]=1e6
    padded,_=p.evaluate('Prosecutor',changed,['SUPPORT'],targets,'SUPPORT','c1')
    assert torch.allclose(lp,padded)


def test_update_and_checkpoint_full_rng(tmp_path):
    t=PPOTrainer(seed=3,epochs=1);obs=observation(); targets={'SUPPORT':['c1','c2'],'REST':[None]}
    rows=[]
    for reward in (0.2,1.):
        d=t.policies.sample('Prosecutor',obs,list(targets),targets,False)
        rows.append(dict(role='Prosecutor',obs=obs,legal=list(targets),targets=targets,**d,value=0.,reward=reward,terminated=reward==1.))
    before=[x.detach().clone() for x in t.policies.parameters()]
    metrics=t.update([rows]);assert np.isfinite(metrics['critic_loss'])
    assert any(not torch.equal(a,b) for a,b in zip(before,t.policies.parameters()))
    path=tmp_path/'v4.pt';t.save(path,{'architecture':'action_centric_v4'})
    expected=(random.random(),np.random.rand(),torch.rand(3))
    restored=PPOTrainer(seed=99);assert restored.load(path)['architecture']=='action_centric_v4'
    actual=(random.random(),np.random.rand(),torch.rand(3))
    assert actual[:2]==expected[:2];assert torch.equal(actual[2],expected[2])
    assert restored.optimizer.state_dict()['state']
    for a,b in zip(t.policies.parameters(),restored.policies.parameters()):assert torch.equal(a,b)
    state=torch.load(path,weights_only=False);state['architecture']='action_centric_v3';torch.save(state,path)
    with pytest.raises(ValueError,match='architecture'):restored.load(path)


def test_public_heuristic_never_reads_gold():
    class PublicEnv:
        state=SimpleNamespace(active_role='Prosecutor',action_stats={})
        @property
        def _gold(self):raise AssertionError('private gold read')
        def legal_actions(self):return ['SUPPORT','REST']
        def legal_targets(self,action):return ['c2'] if action=='SUPPORT' else [None]
    assert heuristic(PublicEnv())==('SUPPORT','c2')

def test_rollout_passes_target_and_records_frozen_masks(monkeypatch):
    import sys
    import types
    module=types.ModuleType('src.courtroom_rl.action_centric_v4.observation')
    module.encode=lambda env:observation()
    monkeypatch.setitem(sys.modules,module.__name__,module)
    class Env:
        state=SimpleNamespace(done=False,active_role='Prosecutor',decision_count=0,action_stats={})
        trace=[]
        def legal_actions(self):return ['SUPPORT']
        def legal_targets(self,action):return ['c2']
        def step(self,action,target):
            assert (action,target)==('SUPPORT','c2')
            self.state.done=True;self.trace.append({})
            return None,1.,True,False,{}
    env=Env();t=PPOTrainer(epochs=1)
    rows=t.rollout(env,demonstration=True)
    assert rows[0]['targets']=={'SUPPORT':['c2']}
    assert rows[0]['target_logprob']==pytest.approx(0.)
    assert env.trace[0]['decision']['target']=='c2'
    assert env.trace[0]['decision']['logprob']==pytest.approx(rows[0]['logprob'])


def test_returns_are_computed_before_role_grouping(monkeypatch):
    import src.courtroom_rl.action_centric_v4.trainer as module
    seen=[]; original=module.global_gae
    def capture(rewards,values,terminated,gamma,lam):
        seen.append((rewards,terminated))
        return original(rewards,values,terminated,gamma,lam)
    monkeypatch.setattr(module,'global_gae',capture)
    t=PPOTrainer(epochs=1);obs=observation();rows=[]
    for role,action,reward,done in [('Prosecutor','REST',-.01,False),('Defender','REST',-.01,False),('Judge','VERDICT',1.,True)]:
        targets={action:[None]};decision=t.policies.sample(role,obs,[action],targets)
        rows.append(dict(role=role,obs=obs,legal=[action],targets=targets,**decision,value=0.,reward=reward,terminated=done))
    t.update([rows])
    assert seen==[([-.01,-.01,1.],[False,False,True])]

def test_progress_displays_public_fallacy_but_step_keeps_id(monkeypatch):
    import sys
    import types
    module=types.ModuleType('src.courtroom_rl.action_centric_v4.observation')
    module.encode=lambda env:observation()
    monkeypatch.setitem(sys.modules,module.__name__,module)
    class Env:
        state=SimpleNamespace(done=False,active_role='Prosecutor',decision_count=0,action_stats={},
            hypotheses=[SimpleNamespace(id='h1',label='Ad Hominem')],
            claims=[SimpleNamespace(claim_id='c2',label='Strawman')])
        trace=[]
        def legal_actions(self):return ['SUPPORT']
        def legal_targets(self,action):return ['c2']
        def step(self,action,target):
            assert target=='c2'
            self.state.done=True;self.trace.append({})
            return None,1.,True,False,{}
    calls=[]
    progress=SimpleNamespace(step=lambda *args:calls.append(args))
    rows=PPOTrainer(epochs=1).rollout(Env(),demonstration=True,progress=progress)
    assert calls[0][2]=='c2 (Strawman)'
    assert rows[0]['target']=='c2'
