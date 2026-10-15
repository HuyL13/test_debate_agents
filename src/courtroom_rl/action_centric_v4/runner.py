"""V4 action/target orchestration; existing data/client/metrics/checkpoints reused."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import collections
import json
import random
import time
import shutil

from src.courtroom_rl.data import ROOT, load_cases, load_development_cases
from src.courtroom_rl.progress import ConsoleProgress
from src.io_utils import append_jsonl, digest, write_json
from src.courtroom_rl.action_centric_v4.env import CourtroomEnv, Budget
from src.courtroom_rl.action_centric_v4.executor import LLMExecutor, FixtureExecutor
from src.courtroom_rl.action_centric_v4.trainer import PPOTrainer, heuristic
def source_migration(previous, current):
    return None
from src.courtroom_rl.action_centric.embeddings import encoder_for


def trace_record(env,case):
    return {'architecture':env.architecture,'sample_id':case.sample_id,'case_input':case.input.as_dict(),
        'budget':asdict(env.budget),'initialization':getattr(env,'initialization',None),'trace':env.trace}


def make_env(case,config,executor,assessor=None,training=False):
    reward=dict(config['reward'])
    if not training:reward['mode']='terminal'
    env=CourtroomEnv(executor,Budget(**config['budget']),assessor=assessor,
        semantic_observation=config.get('observation_mode','structural')=='semantic',
        text_encoder=encoder_for(config,fixture=isinstance(executor,FixtureExecutor)),**reward)
    try:env.reset(case.input,gold=case.gold,sample_id=case.sample_id)
    except Exception as exc:
        exc.courtroom_env=env
        raise
    return env


def record_failure(directory,env,case,transport,start):
    """Retain partial paid dialogue separately from complete PPO episodes."""
    state=env.state if env is not None else None
    if env is not None:
        append_jsonl(directory/'partial_traces.jsonl',{**trace_record(env,case),
            'failure_stage':env.pending_action,'partial_state':env.public_state(),'status':'infrastructure_failure'})
    return {'calls':max(getattr(transport,'calls',0)-start[0],state.calls if state else 0),
        'tokens':max(getattr(transport,'input_tokens',0)+getattr(transport,'output_tokens',0)-start[1]-start[2],
                    state.input_tokens+state.output_tokens if state else 0),
        'decisions':state.decision_count if state else 0,'failure_stage':env.pending_action if env else 'initialization'}


def executor_for(config,directory,fixture,cache,progress):
    from src.courtroom_rl.runner import create_client
    client=create_client(config,directory,fixture,cache)
    executor=FixtureExecutor() if fixture else LLMExecutor(client)
    if hasattr(client.transport,'progress'):client.transport.progress=progress
    return client,executor


def evaluate(cases,config,directory,fixture,policy,trainer=None,seed=0,cache=False,progress=None):
    from src.courtroom_rl.runner import summarize,safe_error,evaluate as legacy_evaluate
    if policy in ('fixed','fixed-original','single','assessor'):
        compatible=deepcopy(config)
        compatible['budget']={k:v for k,v in config['budget'].items() if k in ('max_decisions','max_calls','max_tokens','max_claims')}
        compatible['budget']['max_claims']=min(3,compatible['budget'].get('max_claims',3))
        return legacy_evaluate(cases,compatible,directory,fixture,policy,cache=cache,seed=seed,progress=progress)
    client,executor=executor_for(config,directory,fixture,cache,progress)
    records=[];rng=random.Random(seed)
    for index,case in enumerate(cases):
        row={'sample_id':case.sample_id,'task':'classification','split':case.split,'gold':case.gold}
        transport=client.transport;start=[getattr(transport,k,0) for k in ('calls','input_tokens','output_tokens')]
        env=None
        try:
            env=make_env(case,config,executor)
            if policy=='learned':trainer.rollout(env,True,progress)
            else:
                while not env.state.done:
                    action,target=(lambda a:(a,rng.choice(env.legal_targets(a))))(rng.choice(env.legal_actions())) if policy=='random' else heuristic(env,fixed=policy=='fixed-top3')
                    if progress:progress.step(env.state.active_role,action,target,env.state.decision_count+1)
                    env.step(action,target)
                    env.trace[-1]['decision']={'controller':policy}
            s=env.state
            row.update(status='ok',prediction=s.final_label,calls=s.calls,tokens=s.input_tokens+s.output_tokens,
                decisions=s.decision_count,forced_verdict=s.forced_verdict,estimated_usage_calls=s.estimated_usage_calls,
                top3_hit=case.gold in s.init_labels,initial_top3=s.init_labels,
                role_decisions=dict(collections.Counter(t['role'] for t in env.trace)),
                no_ops=s.no_ops,invalid_actions=s.invalid_actions,claims_created=len(s.claims),
                repeated_claims=sum('Duplicate' in (t.get('error') or '') or 'Repeated' in (t.get('error') or '') for t in env.trace),
                similarity_flagged_claims=sum(bool(c.similarity_review_candidates) for c in s.claims),
                early_stop=not s.forced_verdict)
            append_jsonl(directory/'traces.jsonl',trace_record(env,case))
        except Exception as exc:
            env=getattr(exc,'courtroom_env',env)
            row.update(status='infrastructure_failure',prediction=None,error=safe_error(exc),
                **record_failure(directory,env,case,transport,start))
            if env is not None and env.state.init_labels:
                row.update(initial_top3=env.state.init_labels,top3_hit=case.gold in env.state.init_labels)
        records.append(row);append_jsonl(directory/'predictions.jsonl',row)
        if progress:progress.log('DEV',f'{index+1}/{len(cases)} {row["status"]}'+
            (f': {row["error"]}' if row['status']!='ok' else f' prediction={row["prediction"]} gold={case.gold}'))
    result=summarize(records);good=[r for r in records if r['status']=='ok']
    initialized=[r for r in records if 'initial_top3' in r]
    result.update(fixture=fixture,policy=policy,architecture='action_centric_v4',
        top3_recall=sum(r['top3_hit'] for r in initialized)/len(initialized) if initialized else None,
        top3_recall_scope='all validated initializations, including failed verdict episodes',
        initialized_episodes=len(initialized),
        role_decisions={role:sum(r['role_decisions'].get(role,0) for r in good) for role in ('Prosecutor','Defender','Judge')},
        no_op_rate=sum(r['no_ops'] for r in good)/max(1,sum(r['decisions'] for r in good)),
        invalid_action_rate=sum(r['invalid_actions'] for r in good)/max(1,sum(r['decisions'] for r in good)),
        repeated_claim_rate=sum(r['repeated_claims'] for r in good)/max(1,sum(r['decisions'] for r in good)),
        early_stop_rate=sum(r['early_stop'] for r in good)/len(good) if good else None)
    write_json(directory/'summary.json',result);return result


def dev_subset(cases,limit,seed):
    """Fixed train-independent stratification when the dev size permits all8."""
    if limit>=len(cases):return cases
    rng=random.Random(seed);groups=collections.defaultdict(list)
    for case in cases:groups[case.gold].append(case)
    chosen=[]
    if limit>=8:
        for group in groups.values():chosen.append(rng.choice(group))
    ids={c.sample_id for c in chosen};remaining=[c for c in cases if c.sample_id not in ids]
    rng.shuffle(remaining);return chosen+remaining[:limit-len(chosen)]


def train(args,config,directory,progress):
    from src.courtroom_rl.runner import prepare_assessor,resolved_model,source_hash,safe_error
    mode=config['reward'].get('mode','terminal')
    if mode=='potential' and config['reward'].get('gamma',.99)!=config['ppo']['gamma']:
        raise ValueError('Potential discount must match PPO')
    trainer=PPOTrainer(seed=args.seed,**config['ppo'])
    progress.log('DEVICE',f'Actor/critic: {trainer.device}; LLM: remote API')
    progress.log('REWARD','Terminal +/-1; step/output-token/invalid costs; no proxy shaping')
    assessor=prepare_assessor(config,args.fixture) if mode!='terminal' else None
    train_cases=load_cases('train',ROOT/config['data_dir']);random.Random(args.seed).shuffle(train_cases)
    if args.limit:train_cases=train_cases[:args.limit]
    dev_cases=load_development_cases(config)
    dev_limit=args.dev_limit if args.dev_limit is not None else (len(dev_cases) if config.get('development_set') else 16)
    dev=dev_subset(dev_cases,dev_limit,args.seed)
    progress.log('DEVSET',f'{len(dev)}/{len(dev_cases)} cases; '+
        (f'diagnostic dev from original test: {config["development_set"]["path"]}'
         if config.get('development_set') else 'official dev'))
    manifest={'architecture':'action_centric_v4','config_hash':digest(config),'source_hash':source_hash(),
        'data_provenance':json.loads((ROOT/config['data_dir']/'provenance.json').read_text()),
        'selection_hash':digest([c.sample_id for c in train_cases]),'dev_selection_hash':digest([c.sample_id for c in dev]),
        'model_snapshot':resolved_model(config,args.fixture),'assessor_hash':assessor.fingerprint if assessor else None,
        'tokenizer_hash':None if args.fixture else config.get('tokenizer',{}).get('sha256'),
        'seed':args.seed,'fixture':args.fixture,'epochs_requested':args.epochs,
        'batch_size':args.batch_size,
        'warmup_episodes':args.warmup_episodes,'dev_every':args.dev_every}
    cursor=completed=updates=0;best=-1.;role_counts=collections.Counter()
    resume_history=[]
    if args.resume:
        previous=trainer.load(args.resume)
        migration=None
        for key,value in manifest.items():
            if key=='epochs_requested':
                if value<previous[key]:raise ValueError('Resume epochs cannot be smaller than previous requested total')
                continue
            if key=='source_hash' and previous.get(key)!=value:
                migration=source_migration(previous.get(key),value)
                if migration:continue
            if previous.get(key)!=value:raise ValueError(f'Resume contract differs: {key}')
        cursor,completed,updates,best=(previous[k] for k in ('cursor','completed_episodes','updates','best_dev_macro_f1'))
        role_counts.update(previous.get('role_decisions',{}))
        info={'checkpoint':str(Path(args.resume).resolve()),'cursor':cursor,'completed_episodes':completed,
            'updates':updates,'previous_epochs':previous['epochs_requested'],'target_epochs':args.epochs,
            'previous_source_hash':previous['source_hash'],'current_source_hash':manifest['source_hash'],
            'source_migration':migration}
        resume_history=list(previous.get('resume_history',[]))+[info]
        old_best=Path(args.resume).parent/'best.pt'
        if old_best.is_file():
            import torch
            best_metadata=torch.load(old_best,map_location='cpu',weights_only=False)['metadata']
            compatible=all(best_metadata.get(k)==previous.get(k) for k in
                ('architecture','config_hash','selection_hash','dev_selection_hash','model_snapshot','assessor_hash','fixture'))
            compatible_source=(best_metadata.get('source_hash')==manifest['source_hash'] or
                source_migration(best_metadata.get('source_hash'),manifest['source_hash']) is not None)
            if compatible and compatible_source and best_metadata.get('cursor',0)<=cursor:
                shutil.copy2(old_best,directory/'best.pt');info['inherited_best_checkpoint']=str(old_best.resolve())
        write_json(directory/'resume.json',info)
        progress.log('RESUME',f'Restored actor/critic/optimizer/RNG: attempted={cursor}/{len(train_cases)*args.epochs} '
            f'completed={completed} updates={updates}; epochs total {previous["epochs_requested"]} -> {args.epochs}; warmup skipped')
        if migration:progress.log('RESUME','Explicit compatible source migration: '+migration['reason'])
    client,executor=executor_for(config,directory,args.fixture,False,progress)
    if args.warmup_episodes and not args.resume:
        demos=[]
        for case in train_cases[:args.warmup_episodes]:
            progress.log('WARMUP',f'Train-only heuristic strategy demonstration: {case.sample_id}')
            env=None;transport=client.transport
            usage_start=[getattr(transport,k,0) for k in ('calls','input_tokens','output_tokens')]
            try:
                env=make_env(case,config,executor)
                demos.append(trainer.rollout(env,progress=progress,demonstration=True))
                append_jsonl(directory/'warmup_traces.jsonl',trace_record(env,case))
            except Exception as exc:
                env=getattr(exc,'courtroom_env',env)
                append_jsonl(directory/'warmup_failures.jsonl',{'sample_id':case.sample_id,'error':safe_error(exc),
                    **record_failure(directory,env,case,transport,usage_start)})
                progress.log('ERROR','Warmup demo failed: '+safe_error(exc))
        if not demos:raise ValueError('All warmup demonstrations failed; inspect warmup_failures.jsonl')
        loss=trainer.imitate(demos)
        progress.log('WARMUP',f'Action imitation loss={loss:.4f}; no label supervision, no PPO from demos')
    total=len(train_cases)*args.epochs
    progress.log('START',f'V4 action/target IPPO; train={len(train_cases)} dev={len(dev)} model={manifest["model_snapshot"]["name"]}; '
        f'Actor chooses action and target; LLM writes arguments and verdict; output={directory}')
    while cursor<total:
        trajectories=[];batch_rewards=[]
        progress.log('BATCH',f'Collecting {min(args.batch_size,total-cursor)} episodes; attempted={cursor}/{total}')
        for _ in range(min(args.batch_size,total-cursor)):
            case=train_cases[cursor%len(train_cases)];start=time.monotonic()
            transport=client.transport;usage_start=[getattr(transport,k,0) for k in ('calls','input_tokens','output_tokens')]
            env=None
            progress.log('EPISODE',f'{cursor+1}/{total} sample={case.sample_id}: Top3 initialization')
            try:
                env=make_env(case,config,executor,assessor,True)
                trajectory=trainer.rollout(env,False,progress);trajectories.append(trajectory);completed+=1
                counts=collections.Counter(r['role'] for r in trajectory);role_counts.update(counts)
                reward=sum(r['reward'] for r in trajectory);batch_rewards.append(reward)
                progress.log('EPISODE',f'{cursor+1}/{total} {"correct" if env.state.final_label==case.gold else "wrong"} '
                    f'prediction={env.state.final_label} gold={case.gold} '
                    f'top3_hit={case.gold in env.state.init_labels} reward={reward:+.3f} '
                    f'terminal={sum(t["rewards"]["terminal"] for t in env.trace):+.1f} '
                    f'progress={sum(t["rewards"]["shaping"] for t in env.trace):+.3f} '
                    f'calls={env.state.calls} tokens={env.state.input_tokens+env.state.output_tokens} '
                    f'roles={dict(counts)} forced={env.state.forced_verdict} elapsed={time.monotonic()-start:.1f}s')
                append_jsonl(directory/'traces.jsonl',trace_record(env,case))
            except Exception as exc:
                env=getattr(exc,'courtroom_env',env)
                failure={'sample_id':case.sample_id,'cursor':cursor,'status':'infrastructure_failure','error':safe_error(exc),
                    **record_failure(directory,env,case,transport,usage_start)}
                append_jsonl(directory/'failures.jsonl',failure);progress.log('ERROR',safe_error(exc)+'; failure and usage recorded, excluded from PPO')
            cursor+=1
        loss=trainer.update(trajectories) if trajectories else None
        if loss:updates+=1
        append_jsonl(directory/'updates.jsonl',{'cursor':cursor,'loss':loss,'role_decisions':dict(role_counts)})
        progress.log('PPO',f'update={updates} '+
            (f'actor_loss={loss["actor_loss"]:.4f} critic_loss={loss["critic_loss"]:.4f} '
             f'entropy={loss["entropy"]:.4f} approx_kl={loss["approx_kl"]:.4f}' if loss else 'skipped: no valid episodes')+
            f'; cumulative role coverage={dict(role_counts)}')
        if not role_counts.get('Prosecutor'):progress.log('COVERAGE','No Prosecutor actor decisions yet; consider train-only heuristic warmup/exploration')
        improved=False
        if (loss is not None and updates%args.dev_every==0) or cursor==total:
            result=evaluate(dev,config,directory/f'dev-{cursor:06d}',args.fixture,'learned',trainer,args.seed,progress=progress)
            metrics=result['metrics'] or {};candidate=metrics.get('macro_f1',-1.) if result['coverage']==1 else -1.
            progress.log('DEV',f'accuracy={metrics.get("accuracy")} macro_f1={metrics.get("macro_f1")} '
                f'coverage={result["coverage"]:.1%} top3_recall={result["top3_recall"]}')
            improved=candidate>best
            if improved:best=candidate
        metadata={**manifest,'cursor':cursor,'completed_episodes':completed,'updates':updates,
            'best_dev_macro_f1':best,'role_decisions':dict(role_counts),'resume_history':resume_history}
        trainer.save(directory/'last.pt',metadata)
        if improved:trainer.save(directory/'best.pt',metadata)
        progress.log('CHECKPOINT',f'Saved last.pt; completed={completed}/{cursor} best_macro_f1={best:.4f}')
    result={'architecture':'action_centric_v4','attempted_episodes':cursor,'completed_episodes':completed,
        'failed_episodes':cursor-completed,'updates':updates,'best_dev_macro_f1':best,'fixture':args.fixture,
        'role_decisions':dict(role_counts)}
    write_json(directory/'summary.json',result);progress.log('DONE',str(directory/'summary.json'));return result


def run(args,config):
    from src.courtroom_rl.runner import resolved_model,source_hash
    from src.runner import load_dotenv_file
    if config.get('observation_mode')!='semantic' or config['reward'].get('mode')!='terminal':raise ValueError('V4 requires semantic observations and terminal reward')
    if config['context']!='paper':raise ValueError('V4 uses paper context')
    Budget(**config['budget'])
    if args.command=='train' and (args.cache or args.split not in (None,'train')):raise ValueError('Fresh train-only rollouts required')
    directory=Path(args.output) if args.output else ROOT/'runs'/('courtroom-v4-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    if directory.exists() and any(directory.iterdir()):raise ValueError('Use a new output directory')
    directory.mkdir(parents=True,exist_ok=True);load_dotenv_file(ROOT/'.env')
    resolved=resolved_model(config,args.fixture)
    from src.courtroom_rl.action_centric_v4.observation import OBS_DIMS, ROLE_ACTIONS
    from importlib.metadata import version
    write_json(directory/'run.json',{'architecture':'action_centric_v4','config':config,'resolved_model':resolved,
        'source_hash':source_hash(),'config_hash':digest(config),'seed':args.seed,'fixture':args.fixture,
        'feature_contract':{'role_actions':ROLE_ACTIONS,'observation_dims':OBS_DIMS,'normalization':'bounded0to1-public-only'},
        'packages':{name:version(name) for name in ('torch','numpy','scikit-learn','tokenizers','PyYAML')},
        'sources':json.loads((ROOT/'src/courtroom_rl/vendor/sources.json').read_text())})
    progress=ConsoleProgress(args.log_steps)
    if config.get('observation_mode')=='semantic' and not args.fixture:
        progress.log('EMBEDDING',f'Loading {config.get("embedding",{}).get("model","unconfigured")}; '
            'first use downloads pretrained weights, later uses local cache')
    encoder=encoder_for(config,fixture=args.fixture)
    if encoder is not None:
        progress.log('EMBEDDING','offline fixture encoder' if args.fixture else
            f'{config["embedding"]["model"]}@{config["embedding"]["revision"][:8]} '
            f'device={encoder.device}; frozen CLS + cosine relevance')
    if args.command=='train':return train(args,config,directory,progress)
    policy=args.policy or ('learned' if args.checkpoint else 'heuristic');trainer=None
    if policy=='learned':
        if not args.checkpoint:raise ValueError('Learned policy requires checkpoint')
        trainer=PPOTrainer(seed=args.seed,**config['ppo']);metadata=trainer.load(args.checkpoint)
        for key,value in {'architecture':'action_centric_v4','config_hash':digest(config),'source_hash':source_hash(),
            'fixture':args.fixture,'model_snapshot':resolved}.items():
            if key=='source_hash' and metadata.get(key)!=value and source_migration(metadata.get(key),value):continue
            if metadata.get(key)!=value:raise ValueError(f'Checkpoint differs: {key}')
    split=args.split or ('train' if args.command=='smoke' else 'dev')
    cases=load_development_cases(config) if split=='dev' else load_cases(split,ROOT/config['data_dir'])
    limit=args.limit if args.limit is not None else (1 if args.command=='smoke' else None)
    if limit:cases=cases[:limit]
    result=evaluate(cases,config,directory,args.fixture,policy,trainer,args.seed,args.cache,progress)
    print(json.dumps({'output':str(directory),'successful':result['successful'],'failed':result['failed']}),flush=True)
    return result
