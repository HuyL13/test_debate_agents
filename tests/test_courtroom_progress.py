import threading

import pytest

from src.courtroom_rl.runner import main
from src.courtroom_rl.progress import ConsoleProgress
from src.courtroom_rl.executor import AccountingTransport


def test_train_reports_episode_update_dev_and_checkpoint(tmp_path,capsys):
    main(['train','--fixture','--limit','2','--dev-limit','1','--batch-size','2','--output',str(tmp_path/'run')])
    output = capsys.readouterr().out
    for marker in ('[START]','[BATCH]','[EPISODE]','reward=','calls=','tokens=',
                   '[PPO]','actor_loss=','critic_loss=','[DEV]','macro_f1=','coverage=',
                   '[CHECKPOINT]','last.pt','[DONE]'):
        assert marker in output
    assert output.index('[PPO]') < output.index('[CHECKPOINT]')


def test_api_wait_heartbeat_and_cleanup_after_timeout():
    messages, heartbeat = [], threading.Event()
    def emit(text):
        messages.append(text)
        if 'still waiting' in text:
            heartbeat.set()
    progress = ConsoleProgress(emit=emit,heartbeat_seconds=.01)
    class Blocking:
        def complete(self,payload):
            assert heartbeat.wait(timeout=2)
            raise TimeoutError('private request details must not be printed')
    counted = AccountingTransport(Blocking())
    counted.progress = progress
    counted.progress_context = 'Prosecutor.ACCUSE target=Appeal to Tradition'
    with pytest.raises(TimeoutError):
        counted.complete({'messages':[],'max_completion_tokens':20})
    assert any('attempt=1' in m for m in messages)
    assert any('TimeoutError' in m for m in messages)
    assert all('private request' not in m for m in messages)
    assert not any(t.name.startswith('courtroom-api-heartbeat') for t in threading.enumerate())


def test_verbose_steps_are_optional_and_do_not_change_training(tmp_path,capsys):
    import torch
    base = ['train','--fixture','--limit','1','--dev-limit','1','--seed','3']
    main([*base,'--output',str(tmp_path/'normal')])
    normal_output = capsys.readouterr().out
    main([*base,'--log-steps','--output',str(tmp_path/'verbose')])
    verbose_output = capsys.readouterr().out
    assert '[STEP]' not in normal_output and '[STEP]' in verbose_output
    a = torch.load(tmp_path/'normal/last.pt',weights_only=False)
    b = torch.load(tmp_path/'verbose/last.pt',weights_only=False)
    assert all(torch.equal(a['policies'][k],b['policies'][k]) for k in a['policies'])
