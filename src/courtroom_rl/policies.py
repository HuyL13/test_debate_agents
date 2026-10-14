import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from src.labels import FALLACIES
from src.courtroom_rl.schemas import ACTIONS, ROLES
from src.courtroom_rl.vendor.crew.actor import Actor


TARGETS = (*FALLACIES, 'C1', 'C2', 'C3', None)


class RolePolicies(nn.Module):
    def __init__(self, observation_dim, hidden_dim=64):
        super().__init__()
        self.types = nn.ModuleDict({role: Actor(observation_dim, len(ACTIONS), hidden_dim) for role in ROLES})
        self.targets = nn.ModuleDict({role: Actor(observation_dim+len(ACTIONS), len(TARGETS), hidden_dim) for role in ROLES})

    def distributions(self, role, obs, legal, action=None):
        obs = torch.as_tensor(np.asarray(obs), dtype=torch.float32)
        mask = torch.tensor([a in legal and bool(legal[a]) for a in ACTIONS])
        if not mask.any():
            raise ValueError('No legal actions')
        action_dist = Categorical(logits=self.types[role](obs).masked_fill(~mask, -torch.inf))
        if action is None:
            return action_dist
        if action not in legal:
            raise ValueError('Action missing from rollout mask')
        selected = torch.zeros(len(ACTIONS))
        selected[ACTIONS.index(action)] = 1.
        target_mask = torch.tensor([t in legal[action] for t in TARGETS])
        target_dist = Categorical(logits=self.targets[role](torch.cat([obs, selected])).masked_fill(~target_mask, -torch.inf))
        return action_dist, target_dist

    def sample(self, role, obs, legal, deterministic=False):
        with torch.no_grad():
            dist = self.distributions(role, obs, legal)
            a = dist.probs.argmax() if deterministic else dist.sample()
            action = ACTIONS[int(a)]
            _, targets = self.distributions(role, obs, legal, action)
            t = targets.probs.argmax() if deterministic else targets.sample()
            return {'action': action, 'target': TARGETS[int(t)],
                    'logprob': float(dist.log_prob(a)+targets.log_prob(t))}

    def evaluate(self, role, obs, legal, action, target):
        if target not in legal.get(action, []):
            raise ValueError('Target missing from rollout mask')
        types, targets = self.distributions(role, obs, legal, action)
        return (types.log_prob(torch.tensor(ACTIONS.index(action)))+
                targets.log_prob(torch.tensor(TARGETS.index(target))),
                types.entropy()+targets.entropy())
