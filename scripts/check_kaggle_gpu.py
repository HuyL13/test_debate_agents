"""Offline API-free preflight for actual GPU PPO and pretrained BGE inference."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import numpy as np
    import torch
    import yaml
    from src.courtroom_rl.action_centric.embeddings import encoder_for
    from src.courtroom_rl.action_centric.env import CourtroomEnv
    from src.courtroom_rl.action_centric.executor import FixtureExecutor
    from src.courtroom_rl.action_centric.trainer import PPOTrainer
    from src.data.loader import ModelInput

    assert torch.cuda.is_available(), 'Enable GPU T4 in Kaggle Notebook Settings'
    config = yaml.safe_load((ROOT/'configs/courtroom_rl.kaggle.yaml').read_text())
    print('[GPU]', torch.cuda.get_device_name(0), flush=True)
    print('[EMBEDDING] Loading pinned BGE; first use downloads ~440MB', flush=True)
    encoder = encoder_for(config)
    vectors = encoder.encode(['Traditions must be preserved.', 'It is right because it is traditional.'])
    assert vectors.shape == (2, 768) and np.isfinite(vectors).all()
    assert encoder.device.type == 'cuda'
    trainer = PPOTrainer(**config['ppo'])
    env = CourtroomEnv(FixtureExecutor(), semantic_observation=True, text_encoder=encoder)
    env.reset(ModelInput('Tradition', '', 'It is best because it has always been done.'))
    trainer.update([trainer.rollout(env)])
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'last.pt'
        trainer.save(path, {'fixture': True})
        restored = PPOTrainer(**config['ppo'])
        assert restored.load(path) == {'fixture': True}
        assert all(torch.equal(a,b) for a,b in zip(trainer.policies.parameters(),restored.policies.parameters()))
    assert all(not p.requires_grad and p.grad is None for p in encoder.model.parameters())
    print('[OK] Real BGE + CUDA rollout/PPO update/checkpoint restore; no API calls', flush=True)


if __name__ == '__main__':
    main()
