import json
from pathlib import Path
import pytest
import torch

from src.courtroom_rl.runner import main
from src.courtroom_rl.progress import ConsoleProgress
from src.courtroom_rl.action_centric.env import CourtroomEnv
from src.courtroom_rl.action_centric.executor import FixtureExecutor
from src.courtroom_rl.action_centric.trainer import PPOTrainer
from tests.test_action_centric import CASE


def test_resume_extends_total_epochs_skips_warmup_and_keeps_best(tmp_path,capsys):
    original=tmp_path/'original'
    flags=['train','--fixture','--limit','2','--dev-limit','1','--batch-size','2','--warmup-episodes','1']
    main([*flags,'--epochs','1','--output',str(original)])
    before=torch.load(original/'last.pt',map_location='cpu',weights_only=False)
    resumed=tmp_path/'resumed'
    main([*flags,'--epochs','2','--resume',str(original/'last.pt'),'--output',str(resumed)])
    after=torch.load(resumed/'last.pt',map_location='cpu',weights_only=False)
    assert after['metadata']['cursor']==4 and after['metadata']['updates']==2
    assert after['metadata']['completed_episodes']==4
    assert after['metadata']['epochs_requested']==2
    assert not (resumed/'warmup_traces.jsonl').exists()
    assert (resumed/'best.pt').exists()
    assert (resumed/'resume.json').exists()
    assert any(not torch.equal(before['policies'][k],after['policies'][k]) for k in before['policies'])
    assert '[RESUME]' in capsys.readouterr().out
    # A split run must continue the same optimizer/RNG trajectory as an
    # uninterrupted run, rather than merely reusing trained weights.
    main([*flags,'--epochs','2','--output',str(tmp_path/'uninterrupted')])
    full=torch.load(tmp_path/'uninterrupted/last.pt',map_location='cpu',weights_only=False)
    assert all(torch.equal(after['policies'][k],full['policies'][k]) for k in full['policies'])
    assert all(torch.equal(after['critic'][k],full['critic'][k]) for k in full['critic'])
    assert torch.equal(after['torch_rng'],full['torch_rng'])
    for index,state in full['optimizer']['state'].items():
        assert torch.equal(state['exp_avg'],after['optimizer']['state'][index]['exp_avg'])


def test_action_only_step_logs_no_fake_label_placeholder():
    from types import SimpleNamespace
    output=[];p=ConsoleProgress(True,emit=output.append)
    executor=FixtureExecutor()
    executor.client=SimpleNamespace(transport=SimpleNamespace(progress=p))
    e=CourtroomEnv(executor);e.reset(CASE)
    PPOTrainer(seed=0).rollout(e,progress=p,demonstration=True)
    text='\n'.join(output)
    assert 'LLM-selected' not in text and 'LLM-label' not in text
    assert 'Defender.CHALLENGE' in text
    assert 'fallacy=Appeal to Authority' in text
    assert 'prediction=Slippery Slope' in text


def test_source_migration_only_accepts_registered_exact_pair(tmp_path):
    from src.courtroom_rl.action_centric.resume import source_migration
    p=tmp_path/'migrations.json'
    p.write_text(json.dumps([{'from_source':'old','to_source':'new','reason':'Logging-only compatibility'}]))
    assert source_migration('old','new',p)['reason']
    assert source_migration('old','other',p) is None
    assert source_migration('unknown','new',p) is None


def test_resume_cannot_shrink_requested_epochs(tmp_path):
    flags=['train','--fixture','--limit','1','--dev-limit','1','--batch-size','1']
    main([*flags,'--epochs','2','--output',str(tmp_path/'first')])
    with pytest.raises(ValueError,match='epochs'):
        main([*flags,'--epochs','1','--resume',str(tmp_path/'first/last.pt'),'--output',str(tmp_path/'bad')])
