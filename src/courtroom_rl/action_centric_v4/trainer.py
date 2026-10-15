"""V4 joint action/target PPO, with returns on the shared decision timeline."""
from copy import deepcopy
from pathlib import Path
import random
import numpy as np
import torch
from torch import nn
from src.courtroom_rl.buffer import global_gae
from src.courtroom_rl.action_centric.state import ROLE_ACTIONS
from .policies import RolePolicies, StructuredCritic

ARCHITECTURE = 'action_centric_v4'


def heuristic(env, fixed=False):
    legal = env.legal_actions()
    if env.state.active_role == 'Judge':
        preferred = ('VERDICT',) if fixed else ('REQUEST_SUPPORT','REQUEST_REBUTTAL','VERDICT')
    else:
        preferred = ('SUPPORT','CHALLENGE','REVISE','CONCEDE','REST','PROPOSE_ALTERNATIVE')
    for action in (*preferred, *legal):
        if action in legal:
            targets = env.legal_targets(action)
            if targets:
                return action, targets[0]
    raise ValueError('No publicly eligible action/target')


class PPOTrainer:
    def __init__(self, seed=0, lr=3e-4, gamma=.99, lam=.95, clip=.2, epochs=4, entropy=.01, device='cpu'):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        self.device = torch.device(device)
        if self.device.type == 'cuda' and not torch.cuda.is_available():
            raise ValueError('CUDA requested but unavailable')
        self.policies = RolePolicies().to(self.device)
        self.critic = nn.ModuleDict({r:StructuredCritic() for r in ROLE_ACTIONS}).to(self.device)
        self.optimizer = torch.optim.Adam(list(self.policies.parameters())+list(self.critic.parameters()), lr=lr)
        self.gamma,self.lam,self.clip,self.epochs,self.entropy = gamma,lam,clip,epochs,entropy

    def rollout(self, env, deterministic=False, progress=None, demonstration=False):
        from .observation import encode
        rows=[]
        while not env.state.done:
            role=env.state.active_role; obs=encode(env)
            legal=list(env.legal_actions()); targets={a:list(env.legal_targets(a)) for a in legal}
            if demonstration:
                action,target=heuristic(env)
                with torch.no_grad():
                    lp,_=self.policies.evaluate(role,obs,legal,targets,action,target)
                    ad,tds=self.policies.distributions(role,obs,legal,targets)
                    alp=ad.log_prob(torch.tensor(ROLE_ACTIONS[role].index(action),device=self.device))
                decision=dict(action=action,target=target,logprob=float(lp),action_logprob=float(alp),target_logprob=float(lp-alp))
            else:
                decision=self.policies.sample(role,obs,legal,targets,deterministic)
            if progress:
                target_display=decision['target']
                objects=[*getattr(env.state,'hypotheses',()),*getattr(env.state,'claims',())]
                chosen=next((o for o in objects if getattr(o,'id',getattr(o,'claim_id',None))==target_display),None)
                if chosen is not None:
                    target_display=f'{target_display} ({chosen.label})'
                progress.step(role,decision['action'],target_display,env.state.decision_count+1)
            with torch.no_grad():value=float(self.critic[role](obs))
            _,reward,done,truncated,info=env.step(decision['action'],decision['target'])
            env.trace[-1]['decision']={**decision,'controller':'heuristic-demonstration' if demonstration else 'IPPO',
                'critic_value':value,'deterministic':deterministic,'legal':deepcopy(legal),'targets':deepcopy(targets)}
            rows.append(dict(role=role,obs=deepcopy(obs),legal=legal,targets=targets,**decision,value=value,
                reward=reward,terminated=done,truncated=truncated,
                next_obs=None if done else encode(env),next_role=None if done else env.state.active_role))
        return rows

    def imitate(self, trajectories, epochs=4):
        rows=[r for episode in trajectories for r in episode]
        if not rows:raise ValueError('No train demonstrations')
        for _ in range(epochs):
            loss=-torch.stack([self.policies.evaluate(r['role'],r['obs'],r['legal'],r['targets'],r['action'],r['target'])[0] for r in rows]).mean()
            self.optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policies.parameters(),.5);self.optimizer.step()
        return float(loss.detach())

    def update(self, trajectories):
        rows=[];advantages=[];returns=[]
        for episode in trajectories:
            if not episode or not episode[-1]['terminated']:raise ValueError('Complete scored episode required')
            adv,ret=global_gae([r['reward'] for r in episode],[r['value'] for r in episode],
                               [r['terminated'] for r in episode],self.gamma,self.lam)
            rows.extend(episode);advantages.extend(adv);returns.extend(ret)
        if not rows:raise ValueError('Empty rollout batch')
        adv=torch.tensor(np.asarray(advantages),dtype=torch.float32,device=self.device)
        ret=torch.tensor(np.asarray(returns),dtype=torch.float32,device=self.device)
        for role in ROLE_ACTIONS:
            indexes=[i for i,r in enumerate(rows) if r['role']==role]
            if len(indexes)>1:
                values=adv[indexes];adv[indexes]=(values-values.mean())/(values.std(unbiased=False)+1e-8)
        old_lp=torch.tensor([r['logprob'] for r in rows],dtype=torch.float32,device=self.device)
        for _ in range(self.epochs):
            evaluated=[self.policies.evaluate(r['role'],r['obs'],r['legal'],r['targets'],r['action'],r['target']) for r in rows]
            lp=torch.stack([e[0] for e in evaluated]);entropy=torch.stack([e[1] for e in evaluated]).mean()
            ratio=(lp-old_lp).exp()
            actor_loss=-torch.minimum(ratio*adv,ratio.clamp(1-self.clip,1+self.clip)*adv).mean()
            values=torch.stack([self.critic[r['role']](r['obs']) for r in rows])
            critic_loss=torch.nn.functional.mse_loss(values,ret)
            loss=actor_loss+.5*critic_loss-self.entropy*entropy
            if not torch.isfinite(loss):raise ValueError('Non-finite PPO loss')
            self.optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(list(self.policies.parameters())+list(self.critic.parameters()),.5)
            self.optimizer.step()
        return dict(actor_loss=float(actor_loss.detach()),critic_loss=float(critic_loss.detach()),
                    entropy=float(entropy.detach()),approx_kl=float((old_lp-lp).mean().detach()),
                    role_decisions={role:sum(r['role']==role for r in rows) for role in ROLE_ACTIONS})

    def save(self, path, metadata):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        state=dict(architecture=ARCHITECTURE,device=str(self.device),policies=self.policies.state_dict(),
                   critic=self.critic.state_dict(),optimizer=self.optimizer.state_dict(),metadata=deepcopy(metadata),
                   torch_rng=torch.get_rng_state(),python_rng=random.getstate(),numpy_rng=np.random.get_state(),
                   cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
                   hyperparameters={k:getattr(self,k) for k in ('gamma','lam','clip','epochs','entropy')})
        temporary=path.with_suffix(path.suffix+'.tmp');torch.save(state,temporary);temporary.replace(path)

    def load(self, path):
        # Trusted locally produced artifacts only: pickle-based checkpoints can execute code.
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state.get('architecture') != ARCHITECTURE:raise ValueError('Incompatible checkpoint architecture')
        if state.get('device') != str(self.device):raise ValueError('Checkpoint device mismatch')
        if self.device.type=='cuda' and state.get('cuda_rng') is None:raise ValueError('Missing CUDA RNG')
        self.policies.load_state_dict(state['policies']);self.critic.load_state_dict(state['critic'])
        self.optimizer.load_state_dict(state['optimizer'])
        torch.set_rng_state(state['torch_rng']);random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
        if state.get('cuda_rng') is not None and torch.cuda.is_available():torch.cuda.set_rng_state_all(state['cuda_rng'])
        for key,value in state['hyperparameters'].items():setattr(self,key,value)
        return state['metadata']
