import numpy as np
import pytest
import torch

from src.courtroom_rl.buffer import global_gae
from src.courtroom_rl.policies import RolePolicies
from src.courtroom_rl.trainer import PPOTrainer
from src.courtroom_rl.observation import encode
from tests.test_courtroom_env import environment, accuse


def test_global_gae_propagates_across_other_role_steps():
    adv, ret = global_gae([-.1, -.2, 1.], [0., 0., 0.], [False, False, True], gamma=.9, lam=1.)
    assert ret == pytest.approx([.53, .7, 1.])
    assert adv == pytest.approx(ret)


def test_gae_bootstraps_true_truncation_but_not_terminal():
    assert global_gae([.2], [.3], [False], bootstrap=.5, gamma=.9)[1] == pytest.approx([.65])
    assert global_gae([.2], [.3], [True], bootstrap=.5, gamma=.9)[1] == pytest.approx([.2])


def test_masked_policy_logprob_matches_recomputation():
    torch.manual_seed(3)
    env = environment()
    policies = RolePolicies(len(encode(env)))
    for _ in range(30):
        obs, legal = encode(env), env.legal_actions()
        decision = policies.sample(env.state.active_role, obs, legal)
        assert decision['target'] in legal[decision['action']]
        lp, entropy = policies.evaluate(env.state.active_role, obs, legal, decision['action'], decision['target'])
        assert float(lp.detach()) == pytest.approx(decision['logprob'], abs=1e-6)
        assert torch.isfinite(entropy)


def test_ppo_updates_and_checkpoint_restores(tmp_path):
    trainer = PPOTrainer(seed=2)
    env = environment(max_decisions=5)
    trajectory = trainer.rollout(env)
    before = [p.detach().clone() for p in trainer.policies.parameters()]
    result = trainer.update([trajectory])
    assert all(np.isfinite(v) for v in result.values())
    assert any(not torch.equal(a, b) for a,b in zip(before,trainer.policies.parameters()))
    path = tmp_path/'checkpoint.pt'
    trainer.save(path, {'split':'train'})
    restored = PPOTrainer(seed=99)
    assert restored.load(path)['split'] == 'train'
    assert all(torch.equal(a,b) for a,b in zip(trainer.policies.parameters(), restored.policies.parameters()))
