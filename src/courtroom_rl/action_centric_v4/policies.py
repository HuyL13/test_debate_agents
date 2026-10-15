"""Per-role structured source/object attention and conditional target policies."""
import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical
from src.courtroom_rl.action_centric.state import ROLE_ACTIONS

NO_TARGET = frozenset(('REST', 'VERDICT', 'PROPOSE_ALTERNATIVE'))


class StructuredEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.text = nn.Linear(768, 128)
        self.features = nn.Linear(34, 128)
        self.global_projection = nn.Linear(12, 128)
        self.attention = nn.MultiheadAttention(128, 4, dropout=0., batch_first=True)
        self.norm = nn.LayerNorm(128)

    def forward(self, obs):
        device = self.text.weight.device
        def tensor(key, dtype=torch.float32):
            return torch.as_tensor(np.asarray(obs[key]), dtype=dtype, device=device)
        source = self.text(tensor('source'))
        objects = self.text(tensor('objects')) + self.features(tensor('object_features'))
        history = self.text(tensor('history'))
        # The unmasked source guarantees a finite attention distribution even for empty ledgers.
        tokens = torch.cat((source[None], objects, history), dim=0)[None]
        mask = torch.cat((torch.zeros(1, dtype=torch.bool, device=device),
                          ~tensor('object_mask', torch.bool), ~tensor('history_mask', torch.bool)))[None]
        attended, _ = self.attention(source[None,None], tokens, tokens, key_padding_mask=mask, need_weights=False)
        context = self.norm(source + attended[0,0] + self.global_projection(tensor('global')))
        return context, objects


class RoleActor(nn.Module):
    def __init__(self, actions):
        super().__init__()
        self.encoder = StructuredEncoder()
        self.action_head = nn.Linear(128, actions)
        self.action_embedding = nn.Embedding(actions, 128)
        self.target_query = nn.Linear(128, 128)
        self.target_key = nn.Linear(128, 128)


class StructuredCritic(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = StructuredEncoder()
        self.value = nn.Sequential(nn.Linear(128, 64), nn.Tanh(), nn.Linear(64, 1))

    def forward(self, obs):
        return self.value(self.encoder(obs)[0]).squeeze(-1)


class RolePolicies(nn.Module):
    def __init__(self):
        super().__init__()
        self.actors = nn.ModuleDict({r: RoleActor(len(a)) for r,a in ROLE_ACTIONS.items()})

    def distributions(self, role, obs, legal, targets):
        actor = self.actors[role]
        context, objects = actor.encoder(obs)
        device = context.device
        mask = torch.tensor([a in legal for a in ROLE_ACTIONS[role]], device=device)
        if not mask.any():
            raise ValueError('No legal action types')
        if any(a not in ROLE_ACTIONS[role] for a in legal):
            raise ValueError('Unknown legal action')
        action_dist = Categorical(logits=actor.action_head(context).masked_fill(~mask, -torch.inf))
        conditional = {}
        for action in legal:
            candidates = targets.get(action, [])
            if action in NO_TARGET:
                if list(candidates) != [None]:
                    raise ValueError('No-target action requires [None] target mask')
                conditional[action] = (None, [None])
                continue
            if not candidates or len(set(candidates)) != len(candidates):
                raise ValueError('Empty or duplicate target mask')
            indexes = []
            for target in candidates:
                if target is None or target not in obs['ids']:
                    raise ValueError('Target missing from observation IDs')
                index = obs['ids'].index(target)
                if not obs['object_mask'][index]:
                    raise ValueError('Target points to padded object')
                indexes.append(index)
            ai = ROLE_ACTIONS[role].index(action)
            query = actor.target_query(context + actor.action_embedding.weight[ai])
            logits = actor.target_key(objects[indexes]) @ query / (128 ** .5)
            conditional[action] = (Categorical(logits=logits), list(candidates))
        return action_dist, conditional

    def sample(self, role, obs, legal, targets, deterministic=False, generator=None):
        with torch.no_grad():
            dist, conditional = self.distributions(role, obs, legal, targets)
            ai = dist.probs.argmax() if deterministic else (dist.sample() if generator is None else torch.multinomial(dist.probs,1,generator=generator).squeeze(0))
            action = ROLE_ACTIONS[role][int(ai)]
            td, ids = conditional[action]
            ti = None if td is None else (td.probs.argmax() if deterministic else (td.sample() if generator is None else torch.multinomial(td.probs,1,generator=generator).squeeze(0)))
            target = None if ti is None else ids[int(ti)]
            alp = dist.log_prob(ai)
            tlp = alp.new_zeros(()) if td is None else td.log_prob(ti)
            return dict(action=action, target=target, logprob=float(alp+tlp),
                        action_logprob=float(alp), target_logprob=float(tlp))

    def evaluate(self, role, obs, legal, targets, action, target):
        if action not in legal:
            raise ValueError('Action missing from rollout mask')
        dist, conditional = self.distributions(role, obs, legal, targets)
        td, ids = conditional[action]
        if target not in ids:
            raise ValueError('Target missing from rollout mask')
        ai = torch.tensor(ROLE_ACTIONS[role].index(action), device=dist.logits.device)
        lp = dist.log_prob(ai)
        if td is not None:
            lp = lp + td.log_prob(torch.tensor(ids.index(target), device=lp.device))
        # Exact joint entropy H(A) + E_A H(T|A), not only sampled-action entropy.
        entropy = dist.entropy()
        for a,(target_dist,_) in conditional.items():
            if target_dist is not None:
                entropy = entropy + dist.probs[ROLE_ACTIONS[role].index(a)] * target_dist.entropy()
        return lp, entropy
