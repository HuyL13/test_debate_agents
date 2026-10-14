"""CREW PPO adaptation: role actors, centralized value, global-time GAE.

PPO clipping/normalization/entropy/MSE from CREW train_self_supervised.py.
Original authors: CREW, MIT (vendor/crew/LICENSE).
"""
from copy import deepcopy
from pathlib import Path
import random

import numpy as np
import torch

from src.courtroom_rl.buffer import global_gae
from src.courtroom_rl.observation import OBS_DIM, encode
from src.courtroom_rl.policies import RolePolicies
from src.courtroom_rl.vendor.crew.critic import Critic


class PPOTrainer:
    def __init__(self, seed=0, lr=3e-4, gamma=.99, lam=.95, clip=.2, epochs=4, entropy=.01):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.policies = RolePolicies(OBS_DIM)
        self.critic = Critic(OBS_DIM, 64)
        self.optimizer = torch.optim.Adam(list(self.policies.parameters())+list(self.critic.parameters()), lr=lr)
        self.gamma, self.lam, self.clip, self.epochs, self.entropy = gamma, lam, clip, epochs, entropy

    def rollout(self, env, deterministic=False, progress=None):
        trajectory = []
        while not env.state.done:
            obs, legal, role = encode(env), deepcopy(env.legal_actions()), env.state.active_role
            decision = self.policies.sample(role, obs, legal, deterministic)
            if progress:
                progress.step(role,decision['action'],decision['target'],env.state.decision_count+1)
            with torch.no_grad():
                value = float(self.critic(torch.tensor(obs)).squeeze())
            _, reward, done, truncated, info = env.step(decision['action'], decision['target'])
            env.trace[-1]['decision'] = {'controller':'PPO','action_logprob':decision['logprob'],
                                         'critic_value':value,'deterministic':deterministic}
            trajectory.append({'role': role, 'obs': obs, 'legal': legal, **decision,
                               'value': value, 'reward': reward, 'terminated': done,
                               'truncated': truncated})
        return trajectory

    def update(self, trajectories):
        rows, advantages, returns = [], [], []
        for episode in trajectories:
            if not episode or not episode[-1]['terminated']:
                raise ValueError('PPO expects complete scored episodes')
            adv, ret = global_gae([x['reward'] for x in episode], [x['value'] for x in episode],
                                  [x['terminated'] for x in episode], self.gamma, self.lam)
            rows.extend(episode)
            advantages.extend(adv)
            returns.extend(ret)
        if not rows:
            raise ValueError('Empty rollout batch')
        adv = torch.tensor(advantages, dtype=torch.float32)
        if adv.numel() > 1:
            adv = (adv-adv.mean())/(adv.std(unbiased=False)+1e-8)
        ret = torch.tensor(returns, dtype=torch.float32)
        obs = torch.tensor(np.asarray([r['obs'] for r in rows]), dtype=torch.float32)
        old_lp = torch.tensor([r['logprob'] for r in rows], dtype=torch.float32)
        for _ in range(self.epochs):
            evaluated = [self.policies.evaluate(r['role'], r['obs'], r['legal'], r['action'], r['target']) for r in rows]
            lp = torch.stack([x[0] for x in evaluated])
            entropy = torch.stack([x[1] for x in evaluated]).mean()
            ratio = (lp-old_lp).exp()
            actor_loss = -torch.min(ratio*adv, ratio.clamp(1-self.clip, 1+self.clip)*adv).mean()
            critic_loss = torch.nn.functional.mse_loss(self.critic(obs).squeeze(-1), ret)
            loss = actor_loss+.5*critic_loss-self.entropy*entropy
            if not torch.isfinite(loss):
                raise ValueError('Non-finite PPO loss')
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(list(self.policies.parameters())+list(self.critic.parameters()), .5)
            self.optimizer.step()
        return {'actor_loss': float(actor_loss.detach()), 'critic_loss': float(critic_loss.detach()),
                'entropy': float(entropy.detach()), 'approx_kl': float((old_lp-lp).mean().detach())}

    def save(self, path, metadata):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {'policies': self.policies.state_dict(), 'critic': self.critic.state_dict(),
                 'optimizer': self.optimizer.state_dict(), 'metadata': metadata,
                 'torch_rng': torch.get_rng_state(), 'python_rng': random.getstate(), 'numpy_rng': np.random.get_state(),
                 'hyperparameters': {k: getattr(self,k) for k in ('gamma','lam','clip','epochs','entropy')}}
        temporary = path.with_suffix('.tmp')
        torch.save(state, temporary)
        temporary.replace(path)

    def load(self, path):
        # Only load locally produced trusted checkpoints, never arbitrary downloads.
        state = torch.load(path, map_location='cpu', weights_only=False)
        self.policies.load_state_dict(state['policies'])
        self.critic.load_state_dict(state['critic'])
        self.optimizer.load_state_dict(state['optimizer'])
        torch.set_rng_state(state['torch_rng'])
        random.setstate(state['python_rng'])
        np.random.set_state(state['numpy_rng'])
        for k,v in state['hyperparameters'].items():
            setattr(self,k,v)
        return state['metadata']
