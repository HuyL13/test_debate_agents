"""End-to-end CLI contracts: full dev default, resume and mask replay."""
import json
from types import SimpleNamespace
import yaml
from src.courtroom_rl.data import ROOT
from src.courtroom_rl.action_centric_v4.runner import run
from src.courtroom_rl.action_centric_v4.replay import replay

def test_fixture_full_dev_and_resume(tmp_path):
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    defaults=dict(command='train',fixture=True,cache=False,split=None,seed=0,limit=2,
        dev_limit=None,batch_size=2,epochs=1,warmup_episodes=0,dev_every=10,
        resume=None,log_steps=False,checkpoint=None,policy=None)
    args=SimpleNamespace(**defaults,output=str(tmp_path/'first'))
    result=run(args,config)
    assert result['completed_episodes']==2
    summary=json.loads((tmp_path/'first/dev-000002/summary.json').read_text())
    assert summary['successful']==66 and summary['coverage']==1
    for line in (tmp_path/'first/traces.jsonl').read_text().splitlines():
        assert replay(json.loads(line)).state.done
    args.epochs=2;args.resume=str(tmp_path/'first/last.pt');args.output=str(tmp_path/'resume')
    resumed=run(args,config)
    assert resumed['completed_episodes']==4 and resumed['updates']==2
    assert (tmp_path/'resume/best.pt').exists()
