import threading,time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import numpy as np
import torch
import pytest

def test_episode_pool_overlaps_but_preserves_input_order():
    from src.courtroom_rl.action_centric_v4.parallel import ordered_jobs
    barrier=threading.Barrier(2)
    def work(i):
        barrier.wait(timeout=3);time.sleep(.03 if i==0 else 0);return i
    assert ordered_jobs(work,[0,1],2)==[0,1]

def test_episode_generators_do_not_depend_on_thread_schedule():
    from src.courtroom_rl.action_centric_v4.parallel import episode_generator
    def draw(i):return torch.rand(12,generator=episode_generator('cpu',7,'train',i))
    expected=[draw(i) for i in range(4)]
    with ThreadPoolExecutor(4) as pool:actual=list(pool.map(draw,range(4)))
    assert all(torch.equal(a,b) for a,b in zip(expected,actual))
    assert not torch.equal(expected[0],expected[1])

def test_parallel_eval_isolates_clients_and_excludes_failed_episode(tmp_path,monkeypatch):
    import yaml,json
    from src.courtroom_rl.data import ROOT,load_cases
    from src.courtroom_rl.action_centric_v4 import runner
    from src.courtroom_rl.action_centric_v4.executor import FixtureExecutor
    cases=load_cases('train')[:3];created=[];barrier=threading.Barrier(2)
    class Executor(FixtureExecutor):
        def initialize(self,state,budget):
            if state.sample_id==cases[2].sample_id:raise RuntimeError('provider unavailable')
            barrier.wait(timeout=3)
            return super().initialize(state,budget)
    def factory(config,directory,fixture,cache,progress):
        created.append(directory)
        return SimpleNamespace(transport=SimpleNamespace()),Executor()
    monkeypatch.setattr(runner,'executor_for',factory)
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    result=runner.evaluate(cases,config,tmp_path,True,'fixed-top3',workers=2)
    assert result['successful']==2 and result['failed']==1
    assert len(set(created))==3
    rows=[json.loads(x) for x in (tmp_path/'predictions.jsonl').read_text().splitlines()]
    assert [x['sample_id'] for x in rows]==[c.sample_id for c in cases]
    assert rows[-1]['status']=='infrastructure_failure'


def test_same_training_parameters_with_one_or_three_workers(tmp_path):
    import yaml
    from src.courtroom_rl.data import ROOT
    from src.courtroom_rl.action_centric_v4.runner import run
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    def args(workers):return SimpleNamespace(command='train',fixture=True,cache=False,split=None,seed=9,limit=4,
        dev_limit=2,batch_size=4,epochs=1,warmup_episodes=2,dev_every=10,resume=None,log_steps=False,
        checkpoint=None,policy=None,workers=workers,output=str(tmp_path/f'w{workers}'))
    run(args(1),config);run(args(3),config)
    a=torch.load(tmp_path/'w1/last.pt',weights_only=False);b=torch.load(tmp_path/'w3/last.pt',weights_only=False)
    for kind in ('policies','critic'):
        assert all(torch.equal(value,b[kind][key]) for key,value in a[kind].items())

def test_update_waits_for_all_workers_and_failure_not_in_ppo(tmp_path,monkeypatch):
    import yaml
    from src.courtroom_rl.data import ROOT,load_cases
    from src.courtroom_rl.action_centric_v4 import runner
    from src.courtroom_rl.action_centric_v4.executor import FixtureExecutor
    complete=[];original=runner.collect_episode;update=runner.PPOTrainer.update
    def collect(*args,**kwargs):
        outcome=original(*args,**kwargs);complete.append(args[7]);return outcome
    def checked(self,trajectories):
        assert complete.count('train')==4
        assert len(trajectories)==3
        return update(self,trajectories)
    factory=runner.executor_for;failed=False
    class Fail(FixtureExecutor):
        def initialize(self,state,budget):raise RuntimeError('provider unavailable')
    def clients(config,directory,fixture,cache,progress):
        client,executor=factory(config,directory,fixture,cache,progress)
        if directory.name=='train-000002':executor=Fail()
        return client,executor
    monkeypatch.setattr(runner,'collect_episode',collect);monkeypatch.setattr(runner,'executor_for',clients)
    monkeypatch.setattr(runner.PPOTrainer,'update',checked)
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    args=SimpleNamespace(command='train',fixture=True,cache=False,split=None,seed=0,limit=4,dev_limit=2,
        batch_size=4,epochs=1,warmup_episodes=0,dev_every=10,resume=None,log_steps=False,checkpoint=None,
        policy=None,workers=3,output=str(tmp_path/'train'))
    result=runner.run(args,config)
    assert result['completed_episodes']==3 and result['failed_episodes']==1 and result['updates']==1


def test_previous_v4_resume_migrates_only_with_verified_source_pair(tmp_path,monkeypatch):
    import yaml
    from src.courtroom_rl.data import ROOT
    from src.courtroom_rl.action_centric_v4 import runner
    c=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    a=SimpleNamespace(command='train',fixture=True,cache=False,split=None,seed=0,limit=2,dev_limit=1,
        batch_size=2,epochs=1,warmup_episodes=0,dev_every=10,resume=None,log_steps=False,checkpoint=None,
        policy=None,workers=1,output=str(tmp_path/'first'))
    runner.run(a,c)
    for name in ('last.pt','best.pt'):
        path=tmp_path/'first'/name;state=torch.load(path,weights_only=False)
        state['metadata']['source_hash']='verified-old-v4';state['metadata'].pop('workers');state['metadata'].pop('sampling_contract')
        torch.save(state,path)
    monkeypatch.setattr(runner,'source_migration',lambda old,new:{'reason':'verified previous V4 collector'} if old=='verified-old-v4' else None)
    a.resume=str(tmp_path/'first/last.pt');a.output=str(tmp_path/'resumed');a.epochs=2;a.workers=3
    result=runner.run(a,c)
    assert result['completed_episodes']==4
    assert (tmp_path/'resumed/best.pt').exists()


def test_direct_train_prewarms_one_shared_encoder_before_workers(tmp_path,monkeypatch):
    import yaml
    from src.courtroom_rl.data import ROOT
    from src.courtroom_rl.progress import ConsoleProgress
    from src.courtroom_rl.action_centric_v4 import runner
    from src.courtroom_rl.action_centric.embeddings import FixtureEncoder
    main=threading.get_ident();shared=FixtureEncoder();loaded=False;seen=[]
    def encoder(config,fixture=False):
        nonlocal loaded
        if not loaded:
            assert threading.get_ident()==main,'Concurrent first-use model construction'
            loaded=True
        return shared
    original=runner.make_env
    def env(*args,**kwargs):
        result=original(*args,**kwargs);seen.append(result.text_encoder);return result
    monkeypatch.setattr(runner,'encoder_for',encoder);monkeypatch.setattr(runner,'make_env',env)
    config=yaml.safe_load((ROOT/'configs/courtroom_rl.v4.yaml').read_text())
    a=SimpleNamespace(fixture=True,seed=0,limit=2,dev_limit=1,batch_size=2,epochs=1,
        warmup_episodes=0,dev_every=10,resume=None,workers=2)
    result=runner.train(a,config,tmp_path,ConsoleProgress(emit=lambda text:None))
    assert result['completed_episodes']==2 and all(x is shared for x in seen)
