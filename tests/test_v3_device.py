import pytest
import torch
from src.courtroom_rl.action_centric.trainer import PPOTrainer
from src.courtroom_rl.action_centric.env import CourtroomEnv
from src.courtroom_rl.action_centric.executor import FixtureExecutor
from src.data.loader import ModelInput


@pytest.mark.parametrize('device', ['cpu', 'cuda'])
def test_device_rollout_update_and_resume(tmp_path, device):
    if device == 'cuda' and not torch.cuda.is_available():
        pytest.skip('CUDA hardware unavailable')
    trainer = PPOTrainer(device=device)
    assert next(trainer.policies.parameters()).device.type == device
    env = CourtroomEnv(FixtureExecutor())
    env.reset(ModelInput('Title', '', 'Old practice. Therefore it is best.'))
    trajectory = trainer.rollout(env)
    trainer.update([trajectory])
    path = tmp_path / 'last.pt'
    trainer.save(path, {'cursor': 1})
    restored = PPOTrainer(device=device)
    assert restored.load(path) == {'cursor': 1}
    for a, b in zip(trainer.policies.parameters(), restored.policies.parameters()):
        assert torch.equal(a, b)
    # Restoring RNG must reproduce stochastic actions on the selected device.
    obs, legal = trajectory[0]['obs'], trajectory[0]['legal']
    role = trajectory[0]['role']
    trainer.load(path)
    expected = trainer.policies.sample(role, obs, legal)
    restored.load(path)
    assert restored.policies.sample(role, obs, legal) == expected
