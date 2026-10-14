"""IPPO: action-only role actors/critics and shared global-time returns.

Reuses CREW MLPs, existing global GAE and trusted checkpoint implementation.
"""
import random
from copy import deepcopy
import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical
from src.courtroom_rl.vendor.crew.actor import Actor
from src.courtroom_rl.vendor.crew.critic import Critic
from src.courtroom_rl.trainer import PPOTrainer as CheckpointTrainer
from src.courtroom_rl.buffer import global_gae
from src.courtroom_rl.action_centric.observation import OBS_DIMS, ROLE_ACTIONS, encode


class RolePolicies(nn.Module):
    def __init__(self):
        super().__init__()
        self.actors=nn.ModuleDict({r:Actor(OBS_DIMS[r],len(a),64) for r,a in ROLE_ACTIONS.items()})

    def distribution(self,role,obs,legal):
        device=next(self.parameters()).device
        mask=torch.tensor([a in legal for a in ROLE_ACTIONS[role]],device=device)
        if not mask.any():raise ValueError('No legal action types')
        logits=self.actors[role](torch.as_tensor(np.asarray(obs),dtype=torch.float32,device=device))
        return Categorical(logits=logits.masked_fill(~mask,-torch.inf))

    def sample(self,role,obs,legal,deterministic=False):
        with torch.no_grad():
            dist=self.distribution(role,obs,legal)
            a=dist.probs.argmax() if deterministic else dist.sample()
            return {'action':ROLE_ACTIONS[role][int(a)],'logprob':float(dist.log_prob(a))}

    def evaluate(self,role,obs,legal,action):
        if action not in legal:raise ValueError('Action missing from rollout mask')
        dist=self.distribution(role,obs,legal)
        return dist.log_prob(torch.tensor(ROLE_ACTIONS[role].index(action),device=dist.logits.device)),dist.entropy()


def heuristic(env,fixed=False):
    legal=env.legal_actions();s=env.state
    if s.active_role=='Judge':
        if not fixed and 'REQUEST_SUPPORT' in legal and not s.action_stats.get('Prosecutor.SUPPORT',{}).get('n'):
            return 'REQUEST_SUPPORT'
        return 'VERDICT'
    for action in ('SUPPORT','CHALLENGE','REVISE','REST'):
        if action in legal:return action
    return legal[0]


class PPOTrainer(CheckpointTrainer):
    def __init__(self,seed=0,lr=3e-4,gamma=.99,lam=.95,clip=.2,epochs=4,entropy=.01,device="cpu"):
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        self.device=torch.device(device)
        if self.device.type=="cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA requested but unavailable; enable a GPU or use device=cpu")
        self.policies=RolePolicies().to(self.device)
        self.critic=nn.ModuleDict({r:Critic(dim,64) for r,dim in OBS_DIMS.items()}).to(self.device)
        self.optimizer=torch.optim.Adam(list(self.policies.parameters())+list(self.critic.parameters()),lr=lr)
        self.gamma,self.lam,self.clip,self.epochs,self.entropy=gamma,lam,clip,epochs,entropy

    def rollout(self,env,deterministic=False,progress=None,demonstration=False):
        trajectory=[]
        while not env.state.done:
            role=env.state.active_role;obs=encode(env);legal=list(env.legal_actions())
            if demonstration:
                action=heuristic(env)
                with torch.no_grad():lp,_=self.policies.evaluate(role,obs,legal,action)
                decision={'action':action,'logprob':float(lp)}
            else:decision=self.policies.sample(role,obs,legal,deterministic)
            if progress:progress.step(role,decision['action'],None,env.state.decision_count+1)
            with torch.no_grad():value=float(self.critic[role](torch.tensor(obs,device=self.device)).squeeze())
            _,reward,done,truncated,info=env.step(decision['action'])
            env.trace[-1]['decision']={'controller':'heuristic-demonstration' if demonstration else 'IPPO',
                'action_logprob':decision['logprob'],'critic_value':value,'deterministic':deterministic}
            trajectory.append({'role':role,'obs':obs,'legal':legal,**decision,'value':value,
                'reward':reward,'terminated':done,'truncated':truncated,
                'next_obs':None if done else encode(env),'next_role':None if done else env.state.active_role})
        return trajectory

    def imitate(self,trajectories,epochs=4):
        rows=[r for episode in trajectories for r in episode]
        if not rows:raise ValueError('No train demonstrations')
        for _ in range(epochs):
            loss=-torch.stack([self.policies.evaluate(r['role'],r['obs'],r['legal'],r['action'])[0] for r in rows]).mean()
            self.optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policies.parameters(),.5);self.optimizer.step()
        return float(loss.detach())

    def update(self,trajectories):
        rows,advantages,returns=[],[],[]
        for episode in trajectories:
            if not episode or not episode[-1]['terminated']:raise ValueError('Complete scored episode required')
            adv,ret=global_gae([r['reward'] for r in episode],[r['value'] for r in episode],
                [r['terminated'] for r in episode],self.gamma,self.lam)
            rows.extend(episode);advantages.extend(adv);returns.extend(ret)
        if not rows:raise ValueError('Empty rollout batch')
        adv=torch.tensor(np.asarray(advantages),dtype=torch.float32,device=self.device);ret=torch.tensor(np.asarray(returns),dtype=torch.float32,device=self.device)
        # Normalize per active role, with global-time GAE computed before grouping.
        for role in ROLE_ACTIONS:
            indexes=[i for i,r in enumerate(rows) if r['role']==role]
            if len(indexes)>1:
                values=adv[indexes];adv[indexes]=(values-values.mean())/(values.std(unbiased=False)+1e-8)
        old_lp=torch.tensor([r['logprob'] for r in rows],device=self.device)
        for _ in range(self.epochs):
            evaluated=[self.policies.evaluate(r['role'],r['obs'],r['legal'],r['action']) for r in rows]
            lp=torch.stack([v[0] for v in evaluated]);entropy=torch.stack([v[1] for v in evaluated]).mean()
            ratio=(lp-old_lp).exp()
            actor_loss=-torch.min(ratio*adv,ratio.clamp(1-self.clip,1+self.clip)*adv).mean()
            values=torch.stack([self.critic[r['role']](torch.tensor(r['obs'],device=self.device)).squeeze() for r in rows])
            critic_loss=torch.nn.functional.mse_loss(values,ret)
            loss=actor_loss+.5*critic_loss-self.entropy*entropy
            if not torch.isfinite(loss):raise ValueError('Non-finite IPPO loss')
            self.optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(list(self.policies.parameters())+list(self.critic.parameters()),.5)
            self.optimizer.step()
        return {'actor_loss':float(actor_loss.detach()),'critic_loss':float(critic_loss.detach()),
            'entropy':float(entropy.detach()),'approx_kl':float((old_lp-lp).mean().detach()),
            'role_decisions':{role:sum(r['role']==role for r in rows) for role in ROLE_ACTIONS}}

    def save(self, path, metadata):
        if self.device.type != 'cuda':
            return super().save(path, metadata)
        from pathlib import Path
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {'policies': self.policies.state_dict(), 'critic': self.critic.state_dict(),
                 'optimizer': self.optimizer.state_dict(), 'metadata': metadata,
                 'torch_rng': torch.get_rng_state(), 'python_rng': random.getstate(),
                 'numpy_rng': np.random.get_state(),
                 'cuda_rng': torch.cuda.get_rng_state(self.device),
                 'hyperparameters': {k: getattr(self,k) for k in ('gamma','lam','clip','epochs','entropy')}}
        temporary = path.with_suffix('.tmp')
        torch.save(state, temporary)
        temporary.replace(path)

    def load(self, path):
        state = torch.load(path, map_location='cpu', weights_only=False)
        if self.device.type == 'cuda' and 'cuda_rng' not in state:
            raise ValueError('CUDA resume requires a CUDA checkpoint with RNG state')
        metadata = super().load(path)
        if self.device.type == 'cuda':
            torch.cuda.set_rng_state(state['cuda_rng'], self.device)
        return metadata
