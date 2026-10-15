"""Run: python -m src.courtroom_rl.runner {smoke,evaluate,train,replay,audit}."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import time
import math
from importlib.metadata import version

import yaml

from src.evaluate import score
from src.io_utils import append_jsonl, digest, file_hash, read_jsonl, write_json
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.runner import expand_env, load_dotenv_file
from src.courtroom_rl.baseline import FixtureTransport, run_fixed
from src.courtroom_rl.data import ROOT, load_cases
from src.courtroom_rl.env import Budget, CourtroomEnv
from src.courtroom_rl.executor import LLMExecutor, FixtureExecutor, BudgetExhausted
from src.courtroom_rl.observation import encode
from src.courtroom_rl.replay import replay
from src.courtroom_rl.progress import ConsoleProgress


class NoCache:
    def get(self, key):
        return None
    def put(self, key, value):
        pass


def create_client(config, directory, fixture=False, cache=False):
    load_dotenv_file(ROOT/'.env')
    model = ModelConfig(name='fixture', max_attempts=2, backoff_seconds=0) if fixture else ModelConfig(**expand_env(config['model']))
    cache_path = ROOT/config.get('cache_dir','cache/courtroom_rl')/'responses.sqlite' if cache else directory/'cache.sqlite'
    client = Client(model, cache_path, directory/'api_audit.jsonl', FixtureTransport() if fixture else None)
    if not cache:
        client.cache = NoCache()
    if config.get('architecture') in ('action_centric_v3','action_centric_v4') and config.get('tokenizer') and not fixture:
        from src.courtroom_rl.executor import wrap_accounting
        from src.courtroom_rl.action_centric.token_count import load_counter
        wrap_accounting(client)
        client.transport.input_estimator=load_counter(config,model.name)
    return client


def safe_error(exc):
    text = str(exc)
    for name,value in os.environ.items():
        if value and len(value) > 8 and any(key in name.upper() for key in ('KEY','TOKEN','SECRET','PASSWORD')):
            text = text.replace(value, '[REDACTED]')
    return f'{type(exc).__name__}: {text[:500]}'


def heuristic(env, rng, initial_label=None):
    legal = env.legal_actions()
    if 'ACCUSE' in legal:
        return 'ACCUSE', initial_label or env.labels[0]
    if env.state.active_role == 'Judge':
        # Conservative deterministic comparison baseline. No gold access.
        return 'VERDICT', env.state.charge_label or env.labels[0]
    for action in ('DEFEND_CLAIM','CHALLENGE','CONCEDE','REST_CASE','REST_DEFENSE'):
        if action in legal:
            return action, legal[action][0]
    raise ValueError('Heuristic has no admissible action')


def episode(case, config, executor, policy, rng, trainer=None, deterministic=True, progress=None, assessor=None):
    reward_options = dict(config['reward'])
    if deterministic:
        reward_options['mode'] = 'terminal'
    env = CourtroomEnv(executor, Budget(**config['budget']), assessor=assessor, **reward_options)
    env.reset(case.input, gold=case.gold, sample_id=case.sample_id)
    if policy == 'learned':
        trajectory = trainer.rollout(env, deterministic,progress=progress)
    else:
        trajectory = None
        initial_label = None
        if policy == 'heuristic' and isinstance(executor, LLMExecutor):
            try:
                initial_label = executor.prepare_initial(env.state, env.budget)
            except BudgetExhausted:
                # execute re-raises the prepared accounting failure into the
                # normal environment step, producing a replayable transition.
                initial_label = env.labels[0]
        while not env.state.done:
            legal = env.legal_actions()
            if policy == 'random':
                action = rng.choice(list(legal))
                target = rng.choice(legal[action])
            else:
                action, target = heuristic(env, rng, initial_label)
            env.step(action, target)
            env.trace[-1]['decision'] = {'controller':policy,
                'reason':'Uniform sample from legal action/target lists' if policy == 'random' else
                         'Frozen initial accusation; challenge once; verdict uses current charge'}
    return env, trajectory


def summarize(records):
    successful = [r for r in records if r['status'] == 'ok']
    result = {'attempted':len(records), 'successful':len(successful),
              'failed':len(records)-len(successful), 'coverage':len(successful)/len(records) if records else 0.}
    # Existing score rejects failures. Explicit coverage prevents this conditional
    # metric from being mistaken for accuracy over all attempted samples.
    result['metrics_scope'] = 'successful predictions only; see coverage and failures'
    result['metrics'] = score(successful) if successful else None
    result['correct_over_attempted'] = sum(r['prediction'] == r['gold'] for r in successful)/len(records) if records else 0.
    for field in ('calls','tokens','decisions'):
        values = sorted(r.get(field,0) for r in records)
        if values:
            result[field] = {'mean':statistics.mean(values), 'median':statistics.median(values),
                             'p90':values[max(0, int(.9*len(values)+.999)-1)]}
    result['forced_verdict_rate'] = sum(bool(r.get('forced_verdict')) for r in successful)/len(successful) if successful else 0.
    result['failure_counts'] = {status:sum(r['status'] == status for r in records)
                               for status in sorted({r['status'] for r in records if r['status'] != 'ok'})}
    result['estimated_usage_calls'] = sum(r.get('estimated_usage_calls',0) for r in records)
    result['token_accounting'] = 'provider-reported usage; conservative reservations when usage is unavailable'
    return result


def evaluate(cases, config, directory, fixture, policy, trainer=None, cache=False, seed=0, progress=None):
    if policy == 'assessor':
        from src.courtroom_rl.schemas import CourtState
        from src.labels import FALLACIES
        assessor = prepare_assessor(config,fixture)
        records = []
        for case in cases:
            probabilities = assessor.probabilities(CourtState(case.input,case.sample_id))
            row = {'sample_id':case.sample_id,'task':'classification','split':case.split,'gold':case.gold,
                   'prediction':FALLACIES[int(probabilities.argmax())],'status':'ok','calls':0,'tokens':0,'decisions':0}
            records.append(row)
            append_jsonl(directory/'predictions.jsonl',row)
        summary = {**summarize(records),'fixture':fixture,'policy':policy,'assessor_hash':assessor.fingerprint}
        write_json(directory/'summary.json',summary)
        return summary
    client = create_client(config, directory, fixture, cache)
    executor = FixtureExecutor() if fixture and policy not in ('fixed','fixed-original','single') else LLMExecutor(client)
    if hasattr(client.transport,'progress'):
        client.transport.progress = progress
    records, rng = [], random.Random(seed)
    for index,case in enumerate(cases):
        row = {'sample_id':case.sample_id,'task':'classification','split':case.split,'gold':case.gold}
        start = (getattr(client.transport,'calls',0), getattr(client.transport,'input_tokens',0), getattr(client.transport,'output_tokens',0),getattr(client.transport,'estimated_usage_calls',0))
        try:
            if policy in ('fixed','fixed-original'):
                out = run_fixed(client, case.input, case.sample_id, Budget(**config['budget']),evidence_refs=policy=='fixed')
                row.update(prediction=out['prediction'], calls=out['calls'],tokens=out['input_tokens']+out['output_tokens'], decisions=3,
                           estimated_usage_calls=out['estimated_usage_calls'])
                append_jsonl(directory/'baseline_reports.jsonl', {'sample_id':case.sample_id, **out})
            elif policy == 'single':
                from src.single_llm import run_zero_shot
                client.transport.limits = (client.transport.calls+config['budget']['max_calls'],
                    client.transport.input_tokens+client.transport.output_tokens+config['budget']['max_tokens'])
                out = run_zero_shot(client,'classification',case.input,{'sample_id':case.sample_id,'split':case.split})
                if out.stats.cache_hit and out.stats.total_tokens > config['budget']['max_tokens']:
                    raise BudgetExhausted('Cached single-classifier output exceeds logical budget')
                row.update(prediction=out.output['label'],
                    calls=1 if out.stats.cache_hit else client.transport.calls-start[0],
                    tokens=out.stats.total_tokens if out.stats.cache_hit else
                        client.transport.input_tokens+client.transport.output_tokens-start[1]-start[2],decisions=1,
                    estimated_usage_calls=int(client.cache.last_usage_estimated) if out.stats.cache_hit else client.transport.estimated_usage_calls-start[3])
            else:
                env,_ = episode(case,config,executor,policy,rng,trainer,progress=progress)
                row.update(prediction=env.state.final_label, calls=env.state.calls,
                           tokens=env.state.input_tokens+env.state.output_tokens,
                           decisions=env.state.decision_count, forced_verdict=env.state.forced_verdict,
                           estimated_usage_calls=env.state.estimated_usage_calls)
                row['claims_created'] = len(env.state.claims)
                row['similarity_flagged_claims'] = sum(bool(c.similarity_review_candidates) for c in env.state.claims)
                append_jsonl(directory/'traces.jsonl', {'sample_id':case.sample_id,'case_input':case.input.as_dict(),
                    'budget':config['budget'], 'trace':env.trace})
            row['status'] = 'ok'
        except Exception as exc:
            row.update(status='budget_exhausted' if isinstance(exc,BudgetExhausted) else 'infrastructure_failure',prediction=None,error=safe_error(exc),
                       calls=getattr(client.transport,'calls',0)-start[0],
                       tokens=getattr(client.transport,'input_tokens',0)+getattr(client.transport,'output_tokens',0)-start[1]-start[2],
                       estimated_usage_calls=getattr(client.transport,'estimated_usage_calls',0)-start[3])
        records.append(row)
        append_jsonl(directory/'predictions.jsonl',row)
        if row['status'] != 'ok' or (index+1) % max(1,len(cases)//10) == 0 or index+1 == len(cases):
            if progress:
                progress.log('DEV',f'case {index+1}/{len(cases)} {row["status"]}'+(f': {row["error"]}' if row['status'] != 'ok' else ''))
            else:
                print(f'{policy}: {index+1}/{len(cases)} {row["status"]}',flush=True)
    summary = summarize(records)
    summary.update(fixture=fixture,policy=policy)
    write_json(directory/'summary.json',summary)
    return summary


def prepare_assessor(config, fixture=False):
    from src.courtroom_rl.assessor import FrozenAssessor, UniformAssessor
    if fixture:
        return UniformAssessor()
    options = config.get('assessor', {})
    rows = load_cases('train', ROOT/config['data_dir'])
    expected = digest([(c.sample_id,c.article_id,c.input.as_dict(),c.gold) for c in rows])
    path = ROOT/options.get('path','cache/courtroom_rl/assessor.joblib')
    seed, features = options.get('seed',0), options.get('max_features',20000)
    if path.exists():
        assessor = FrozenAssessor.load(path)
        if (assessor.metadata['data_hash'],assessor.metadata['seed'],assessor.metadata['max_features']) != (expected,seed,features):
            raise ValueError('Assessor dataset/settings differ; select a new artifact path')
    else:
        assessor = FrozenAssessor.fit(rows,seed=seed,max_features=features)
        assessor.save(path)
    return assessor


def train(args, config, directory):
    progress = ConsoleProgress(verbose_steps=args.log_steps)
    progress.log('START',f'Preparing CPU PPO and verified train/dev data; output={directory}')
    from src.courtroom_rl.trainer import PPOTrainer
    trainer = PPOTrainer(seed=args.seed,**config['ppo'])
    mode = config['reward'].get('mode','terminal')
    if mode == 'potential' and config['reward'].get('gamma',.99) != config['ppo']['gamma']:
        raise ValueError('Potential reward gamma must equal PPO gamma')
    progress.log('ASSESSOR',f'reward={mode}; preparing frozen train-only CPU scorer')
    assessor = prepare_assessor(config,args.fixture) if mode != 'terminal' else None
    train_cases = load_cases('train', ROOT/config['data_dir'])
    random.Random(args.seed).shuffle(train_cases)
    if args.limit:
        train_cases = train_cases[:args.limit]
    dev_cases = load_cases('dev', ROOT/config['data_dir'])[:args.dev_limit]
    manifest = {'config_hash':digest(config), 'selection_hash':digest([c.sample_id for c in train_cases]),
                'seed':args.seed, 'fixture':args.fixture,'split':'train',
                'model_snapshot':resolved_model(config,args.fixture), 'data_provenance':json.loads((ROOT/config['data_dir']/'provenance.json').read_text()),
                'source_hash':source_hash(), 'epochs_requested':args.epochs,
                'dev_selection_hash':digest([c.sample_id for c in dev_cases]),
                'assessor_hash':assessor.fingerprint if assessor else None}
    cursor, completed, best, updates = 0,0,-1.,0
    if args.resume:
        previous = trainer.load(args.resume)
        for key in ('config_hash','selection_hash','seed','fixture','source_hash','epochs_requested','model_snapshot','data_provenance','dev_selection_hash','assessor_hash'):
            if previous[key] != manifest[key]:
                raise ValueError(f'Resume contract differs: {key}')
        cursor,completed,best,updates = previous['cursor'],previous['completed_episodes'],previous['best_dev_macro_f1'],previous['updates']
    client = create_client(config,directory,args.fixture,False)
    executor = FixtureExecutor() if args.fixture else LLMExecutor(client)
    total = len(train_cases)*args.epochs
    if hasattr(client.transport,'progress'):
        client.transport.progress = progress
    progress.log('START',f'model={manifest["model_snapshot"]["name"]} train={len(train_cases)} dev={len(dev_cases)} '
        f'epochs={args.epochs} batch_size={args.batch_size} seed={args.seed} fixture={args.fixture}; '
        f'budget decisions/calls/tokens={config["budget"]["max_decisions"]}/{config["budget"]["max_calls"]}/{config["budget"]["max_tokens"]}')
    if args.resume:
        progress.log('RESUME',f'{args.resume}: attempted={cursor}/{total} completed={completed} updates={updates}')
    batches = math.ceil(total/args.batch_size)
    while cursor < total:
        trajectories = []
        batch_stats = []
        progress.log('BATCH',f'{cursor//args.batch_size+1}/{batches}: collecting up to {min(args.batch_size,total-cursor)} episodes')
        for _ in range(min(args.batch_size,total-cursor)):
            case = train_cases[cursor % len(train_cases)]
            episode_started = time.monotonic()
            progress.log('EPISODE',f'{cursor+1}/{total} epoch={cursor//len(train_cases)+1}/{args.epochs} sample={case.sample_id}: rollout started')
            try:
                env,trajectory = episode(case,config,executor,'learned',random.Random(args.seed),trainer,False,progress=progress,assessor=assessor)
                trajectories.append(trajectory)
                completed += 1
                reward = sum(t['reward'] for t in trajectory)
                correct = env.state.final_label == case.gold
                batch_stats.append((reward,correct,env.state.forced_verdict))
                progress.log('EPISODE',f'{cursor+1}/{total} sample={case.sample_id}: {"correct" if correct else "wrong"} '
                    f'reward={reward:+.3f} terminal={sum(t["rewards"]["terminal"] for t in env.trace):+.1f} '
                    f'progress={sum(t["rewards"]["shaping"] for t in env.trace):+.3f} decisions={env.state.decision_count} calls={env.state.calls} '
                    f'tokens={env.state.input_tokens+env.state.output_tokens}'
                    f'{" (includes estimates)" if env.state.estimated_usage_calls else ""} '
                    f'stop={"budget/forced verdict" if env.state.forced_verdict else "judge verdict"} '
                    f'elapsed={time.monotonic()-episode_started:.1f}s')
                append_jsonl(directory/'traces.jsonl',{'sample_id':case.sample_id,'case_input':case.input.as_dict(),
                    'budget':config['budget'],'trace':env.trace})
            except Exception as exc:
                append_jsonl(directory/'failures.jsonl',{'sample_id':case.sample_id,'cursor':cursor,'status':'infrastructure_failure','error':safe_error(exc)})
                progress.log('ERROR',f'sample={case.sample_id} excluded from PPO after {time.monotonic()-episode_started:.1f}s: '
                    f'{safe_error(exc)}; details={directory/"failures.jsonl"}')
            cursor += 1
        progress.log('PPO',f'Updating from {len(trajectories)} valid episodes / {sum(len(t) for t in trajectories)} decisions')
        loss = trainer.update(trajectories) if trajectories else None
        if trajectories:
            updates += 1
        if loss:
            progress.log('PPO',f'update={updates} actor_loss={loss["actor_loss"]:.4f} critic_loss={loss["critic_loss"]:.4f} '
                f'entropy={loss["entropy"]:.4f} approx_kl={loss["approx_kl"]:.4f}; '
                f'batch reward_mean={statistics.mean(s[0] for s in batch_stats):+.3f} '
                f'acc={statistics.mean(s[1] for s in batch_stats):.1%} forced={statistics.mean(s[2] for s in batch_stats):.1%}')
        else:
            progress.log('PPO','Skipped update: no valid episodes in this batch')
        append_jsonl(directory/'updates.jsonl',{'cursor':cursor,'loss':loss})
        # Frozen greedy policy on dev; gold used only by score/reward, no optimizer.
        progress.log('DEV',f'Starting frozen-policy validation on {len(dev_cases)} cases (no optimizer updates)')
        validation = evaluate(dev_cases,config,directory/f'dev-{cursor:06d}',args.fixture,'learned',trainer,seed=args.seed,progress=progress)
        metrics = validation['metrics'] or {}
        dev_accuracy = f'{metrics["accuracy"]:.1%}' if metrics else 'n/a'
        dev_f1 = f'{metrics["macro_f1"]:.4f}' if metrics else 'n/a'
        progress.log('DEV',f'acc_success={dev_accuracy} macro_f1={dev_f1} '
            f'coverage={validation["coverage"]:.1%} failed={validation["failed"]} forced={validation["forced_verdict_rate"]:.1%}')
        candidate = validation['metrics']['macro_f1'] if validation['metrics'] and validation['coverage'] == 1 else -1.
        improved = candidate > best
        if improved:
            best = candidate
        metadata = {**manifest,'cursor':cursor,'completed_episodes':completed,'best_dev_macro_f1':best,'updates':updates}
        trainer.save(directory/'last.pt',metadata)
        if improved:
            trainer.save(directory/'best.pt',metadata)
        progress.log('CHECKPOINT',f'Saved {directory/"last.pt"}'+
            (f'; new best dev macro_f1={best:.4f} -> {directory/"best.pt"}' if improved else
             f'; best unchanged ({best:.4f})' if best >= 0 else '; best unavailable: dev coverage incomplete'))
        progress.log('TRAIN',f'attempted={cursor}/{total} completed={completed} excluded={cursor-completed} updates={updates}')
    summary = {'attempted_episodes':cursor,'completed_episodes':completed,'failed_episodes':cursor-completed,
               'updates':updates,'best_dev_macro_f1':best,'fixture':args.fixture,
               'note':'Fixture verifies plumbing only.' if args.fixture else 'Model selection uses dev only.'}
    write_json(directory/'summary.json',summary)
    progress.log('DONE',f'attempted={cursor}/{total} completed={completed} excluded={cursor-completed} updates={updates}; '
        f'summary={directory/"summary.json"}')
    return summary


def source_hash():
    paths = set((ROOT/'src/courtroom_rl').rglob('*.py')) | set((ROOT/'src/llm').glob('*.py'))
    paths.update(ROOT/p for p in ('src/data/loader.py','src/schemas.py','src/labels.py','src/io_utils.py','src/evaluate.py','src/runner.py','src/evidence.py',
                                'src/courtroom_rl/vendor/sources.json'))
    return digest({str(p.relative_to(ROOT)):file_hash(p) for p in sorted(paths)})


def resolved_model(config, fixture):
    if fixture:
        return {'name':'fixture','provider':'fixture'}
    return {k:v for k,v in asdict(ModelConfig(**expand_env(config['model']))).items() if 'key' not in k}


def audit(directory):
    from src.data.loader import load_split, select_task
    from sklearn.feature_extraction.text import HashingVectorizer
    import numpy as np
    cases = {s:load_cases(s) for s in ('train','dev','test')}
    report = {'splits':{},'overlaps':{}}
    provenance = json.loads((ROOT/'data/cocolofa/provenance.json').read_text())
    for split,items in cases.items():
        raw_path = ROOT/f'data/cocolofa/{split}.json'
        loaded = select_task(load_split(raw_path),'classification')
        report['splits'][split] = {'count':len(items), 'raw_hash_matches_provenance':file_hash(raw_path)==provenance['sha256'][f'{split}.json'],
            'flat_matches_loader': [(c.sample_id,c.gold,c.input.as_dict()) for c in items] == [(s.sample_id,s.gold('classification'),s.model_input().as_dict()) for s in loaded]}
        upstream = ROOT/'upstream/cocolofa'
        if (upstream/'.git').exists():
            pinned = subprocess.run(['git','-C',str(upstream),'show',f'{provenance["commit"]}:{split}.json'],capture_output=True)
            if pinned.returncode == 0:
                report['splits'][split]['raw_json_equals_pinned_commit'] = json.loads(raw_path.read_text(encoding='utf-8-sig')) == json.loads(pinned.stdout)
    vectorizer = HashingVectorizer(analyzer='char',ngram_range=(3,5),n_features=2**16,alternate_sign=False,norm='l2')
    features = {s:vectorizer.transform([c.input.comment for c in rows]) for s,rows in cases.items()}
    for left,right in [('train','dev'),('train','test'),('dev','test')]:
        normalized = lambda text:' '.join(text.casefold().split())
        lookup = {}
        for c in cases[left]:
            lookup.setdefault(normalized(c.input.comment),[]).append(c.sample_id)
        exact = [[a,c.sample_id] for c in cases[right] for a in lookup.get(normalized(c.input.comment),[])]
        similarities = features[left] @ features[right].T
        coo = similarities.tocoo()
        near = [[cases[left][int(a)].sample_id,cases[right][int(b)].sample_id,round(float(v),5)]
                for a,b,v in zip(coo.row,coo.col,coo.data) if v >= .95]
        report['overlaps'][f'{left}-{right}'] = {'shared_article_ids':sorted({c.article_id for c in cases[left]} & {c.article_id for c in cases[right]}),
            'exact_normalized_comment_pairs':exact, 'near_duplicate_candidates':near,
            'near_duplicate_method':'hashed character 3-5gram cosine >= .95; candidates only, includes exact duplicates'}
    write_json(directory/'data_audit.json',report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['smoke','evaluate','train','replay','audit','prepare-assessor'])
    parser.add_argument('--reward-mode',choices=['crew','terminal','potential'])
    parser.add_argument('--config',default=str(ROOT/'configs/courtroom_rl.yaml'))
    parser.add_argument('--fixture',action='store_true')
    parser.add_argument('--limit',type=int,default=None)
    parser.add_argument('--dev-limit',type=int,default=None,help='Default: full configured diagnostic dev; otherwise16')
    parser.add_argument('--workers',type=int,default=None,help='V4 concurrent episode workers; default from config')
    parser.add_argument('--batch-size',type=int,default=8)
    parser.add_argument('--epochs',type=int,default=1)
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--split',choices=['train','dev','test'],default=None)
    parser.add_argument('--policy',choices=['heuristic','random','learned','fixed','fixed-original','fixed-top3','single','assessor'],default=None)
    parser.add_argument('--checkpoint')
    parser.add_argument('--resume')
    parser.add_argument('--cache',action='store_true',help='Evaluation only; costs still count logical usage')
    parser.add_argument('--log-steps',action='store_true',help='Print each role/action/target in train and validation rollouts')
    parser.add_argument('--warmup-episodes',type=int,default=0,help='V3 train-only heuristic action imitation episodes')
    parser.add_argument('--dev-every',type=int,default=4,help='V3 validation interval in PPO updates; final batch always validates')
    parser.add_argument('--observation-mode',choices=['structural','semantic'])
    parser.add_argument('--output')
    parser.add_argument('--trace')
    args = parser.parse_args(argv)
    if args.warmup_episodes<0 or args.dev_every<1:
        parser.error('warmup episodes must be nonnegative and dev interval positive')
    for key in ('limit','dev_limit','batch_size','epochs'):
        value = getattr(args,key)
        if value is not None and value < 1:
            parser.error(f'--{key.replace("_","-")} must be positive')
    if args.workers is not None and args.workers<1:parser.error('--workers must be positive')
    if args.command == 'replay':
        if not args.trace:
            parser.error('replay requires --trace')
        from src.data.loader import ModelInput
        records = read_jsonl(args.trace)
        for row in records:
            if row.get('architecture')=='action_centric_v4':
                from src.courtroom_rl.action_centric_v4.replay import replay as replay_v4
                replay_v4(row)
            elif row.get('architecture')=='action_centric_v3':
                from src.courtroom_rl.action_centric.replay import replay as replay_v3
                replay_v3(row)
            else:
                replay(ModelInput(**row['case_input']),row['trace'],Budget(**row['budget']),row['sample_id'])
        print(f'Replayed {len(records)} episodes with matching states/verdicts.')
        return
    config = yaml.safe_load(Path(args.config).read_text(encoding='utf-8-sig'))
    if args.reward_mode:
        config['reward']['mode'] = args.reward_mode
    if args.observation_mode:
        config['observation_mode']=args.observation_mode
    if args.workers is not None and config.get('architecture')!='action_centric_v4':
        raise ValueError('--workers is currently supported by V4 only')
    if args.command == 'prepare-assessor':
        assessor = prepare_assessor(config,args.fixture)
        print(json.dumps({'assessor_hash':assessor.fingerprint,'fixture':args.fixture}))
        return
    if config.get('architecture')=='action_centric_v4' and args.command in ('smoke','evaluate','train'):
        from src.courtroom_rl.action_centric_v4.runner import run
        return run(args,config)
    if config.get('architecture')=='action_centric_v3' and args.command in ('smoke','evaluate','train'):
        from src.courtroom_rl.action_centric.runner import run
        return run(args,config)
    if args.dev_limit is None:
        args.dev_limit=16
    if config['context'] != 'paper':
        raise ValueError('V1 uses fixed paper context')
    if args.command == 'train' and (args.cache or args.split not in (None,'train')):
        parser.error('Training uses only train and fresh rollouts')
    directory = Path(args.output) if args.output else ROOT/'runs'/('courtroom-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Use a new output directory; existing runs are never overwritten')
    directory.mkdir(parents=True,exist_ok=True)
    load_dotenv_file(ROOT/'.env')
    # Snapshot resolved public model settings, never credentials.
    resolved = resolved_model(config,args.fixture)
    packages = {}
    for name in ('torch','numpy','PyYAML','jsonschema','pytest'):
        try:
            packages[name] = version(name)
        except Exception:
            packages[name] = 'not installed'
    write_json(directory/'run.json',{'config':config,'resolved_model':resolved,'config_hash':digest(config),
        'source_hash':source_hash(),'seed':args.seed,'fixture':args.fixture,'command':args.command,
        'packages':packages,'sources':json.loads((ROOT/'src/courtroom_rl/vendor/sources.json').read_text())})
    if args.command == 'audit':
        return audit(directory)
    if args.command == 'train':
        result = train(args,config,directory)
    else:
        split = args.split or ('train' if args.command == 'smoke' else 'dev')
        cases = load_cases(split,ROOT/config['data_dir'])
        limit = args.limit if args.limit is not None else (1 if args.command == 'smoke' else None)
        if limit:
            cases = cases[:limit]
        policy = args.policy or ('learned' if args.checkpoint else 'heuristic')
        trainer = None
        if policy == 'learned':
            if not args.checkpoint:
                parser.error('learned evaluation requires --checkpoint')
            from src.courtroom_rl.trainer import PPOTrainer
            trainer = PPOTrainer(seed=args.seed,**config['ppo'])
            metadata = trainer.load(args.checkpoint)
            if metadata['config_hash'] != digest(config) or metadata['fixture'] != args.fixture or metadata['source_hash'] != source_hash() or metadata['model_snapshot'] != resolved:
                raise ValueError('Checkpoint configuration/source/fixture differs')
        result = evaluate(cases,config,directory,args.fixture,policy,trainer,args.cache,args.seed)
    metrics = result.get('metrics') or {}
    console = {k:result[k] for k in ('attempted','successful','failed','completed_episodes','updates','fixture') if k in result}
    console.update({k:metrics[k] for k in ('accuracy','macro_f1') if k in metrics})
    print(json.dumps({'output':str(directory),**console},ensure_ascii=False),flush=True)
    return result


if __name__ == '__main__':
    result = main()
    if result and (result.get('failed',0) or result.get('failed_episodes',0)):
        raise SystemExit(1)
