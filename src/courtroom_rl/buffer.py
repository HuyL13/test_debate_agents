"""CREW backward GAE recurrence adapted to one global event timeline.

Original: CREW src/training/ippo_trainer.py, MIT (vendor/crew/LICENSE).
Do not remove other roles' costs or bootstrap across episode boundaries.
"""
import numpy as np


def global_gae(rewards, values, terminated, gamma=.99, lam=.95, bootstrap=0.):
    if not len(rewards) == len(values) == len(terminated):
        raise ValueError('Timeline lengths differ')
    advantages = np.zeros(len(rewards), dtype=np.float32)
    gae = 0.
    for t in reversed(range(len(rewards))):
        next_value = values[t+1] if t+1 < len(values) else bootstrap
        continuation = 1.-float(terminated[t])
        delta = rewards[t]+gamma*next_value*continuation-values[t]
        gae = delta+gamma*lam*continuation*gae
        advantages[t] = gae
    return advantages, advantages+np.asarray(values, dtype=np.float32)
