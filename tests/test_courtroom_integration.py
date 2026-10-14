import json
from dataclasses import replace

import pytest

from src.data.loader import ModelInput
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.courtroom_rl.executor import LLMExecutor, AccountingTransport, BudgetExhausted
from src.courtroom_rl.env import Budget, CourtroomEnv
from src.courtroom_rl.baseline import run_fixed, FixtureTransport
from src.courtroom_rl.data import load_cases
from src.courtroom_rl.runner import main
from tests.test_courtroom_env import TEXT, LABEL


def test_action_client_grounding_retries_and_charges_every_attempt(tmp_path):
    class RetryTransport(FixtureTransport):
        def __init__(self):
            self.requests = []
        def complete(self, payload):
            self.requests.append(payload)
            response = super().complete(payload)
            if len(self.requests) == 1:
                obj = json.loads(response['choices'][0]['message']['content'])
                obj['evidence_ids'] = ['T999']
                response['choices'][0]['message']['content'] = json.dumps(obj)
            return response
    transport = RetryTransport()
    client = Client(ModelConfig('fixture', max_attempts=2, backoff_seconds=0), tmp_path/'cache.jsonl', tmp_path/'audit.jsonl', transport)
    env = CourtroomEnv(LLMExecutor(client))
    env.reset(ModelInput('', '', TEXT), gold=LABEL)
    env.step('ACCUSE', LABEL)
    assert env.state.calls == 2
    assert env.state.input_tokens == 50
    assert env.state.output_tokens == 50
    serialized = json.dumps(transport.requests)
    assert 'gold' not in serialized and 'reward' not in serialized


def test_fixed_baseline_keeps_three_stage_contract(tmp_path):
    client = Client(ModelConfig('fixture'), tmp_path/'cache.jsonl', tmp_path/'audit.jsonl', FixtureTransport())
    result = run_fixed(client, ModelInput('', '', TEXT), 'example')
    assert result['prediction'] == 'Appeal to Authority'
    assert result['calls'] == 3
    assert list(result['reports']) == ['Prosecutor', 'Defender', 'DialecticalArbiter']


def test_all_classification_files_have_verified_eight_label_records():
    from src.data.loader import load_split, select_task
    from src.courtroom_rl.data import ROOT
    for split, count in [('train',3168), ('dev',927), ('test',481)]:
        cases = load_cases(split)
        assert len(cases) == count
        assert len({c.gold for c in cases}) == 8
        assert all(set(c.input.as_dict()) == {'title','parent_comment','comment'} for c in cases)
        original = select_task(load_split(ROOT/f'data/cocolofa/{split}.json'),'classification')
        assert [(c.sample_id,c.gold,c.input.as_dict()) for c in cases] == [(s.sample_id,s.gold('classification'),s.model_input().as_dict()) for s in original]


def test_fixed_baseline_obeys_decision_cap(tmp_path):
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',FixtureTransport())
    with pytest.raises(BudgetExhausted):
        run_fixed(client,ModelInput('', '', TEXT),'sample',Budget(max_decisions=1))
    assert client.transport.calls == 1


def test_runner_fixture_train_evaluate_resume_and_replay(tmp_path):
    out = tmp_path/'train'
    main(['train','--fixture','--limit','3','--dev-limit','2','--batch-size','2','--output',str(out)])
    assert (out/'last.pt').is_file() and (out/'best.pt').is_file()
    summary = json.loads((out/'summary.json').read_text())
    assert summary['completed_episodes'] == 3
    resumed = tmp_path/'resumed'
    main(['train','--fixture','--limit','3','--dev-limit','2','--batch-size','2','--resume',str(out/'last.pt'),'--output',str(resumed)])
    assert json.loads((resumed/'summary.json').read_text())['completed_episodes'] == 3
    evaluation = tmp_path/'eval'
    main(['evaluate','--fixture','--limit','2','--checkpoint',str(out/'best.pt'),'--output',str(evaluation)])
    report = json.loads((evaluation/'summary.json').read_text())
    assert report['attempted'] == report['successful'] == 2
    assert report['metrics']['count'] == 2
    main(['replay','--trace',str(evaluation/'traces.jsonl')])


def test_accounting_transport_enforces_call_cap():
    transport = AccountingTransport(FixtureTransport())
    transport.limits = (0, 10000)
    with pytest.raises(BudgetExhausted):
        transport.complete({'messages':[], 'max_completion_tokens':10})
    assert transport.calls == 0


def test_heuristic_initial_charge_reuses_one_prosecutor_call(tmp_path):
    client = Client(ModelConfig('fixture'), tmp_path/'cache', tmp_path/'audit', FixtureTransport())
    executor = LLMExecutor(client)
    env = CourtroomEnv(executor)
    env.reset(ModelInput('', '', TEXT), gold=LABEL)
    label = executor.prepare_initial(env.state, env.budget)
    env.step('ACCUSE', label)
    assert env.state.calls == client.transport.calls == 1
    assert env.state.charge_label == 'Appeal to Authority'


def test_environment_small_token_budget_stops_before_request(tmp_path):
    client = Client(ModelConfig('fixture'), tmp_path/'cache', tmp_path/'audit', FixtureTransport())
    env = CourtroomEnv(LLMExecutor(client), Budget(max_tokens=1))
    env.reset(ModelInput('', '', TEXT), gold=LABEL)
    env.step('ACCUSE', LABEL)
    assert env.state.calls == 0 and env.state.forced_verdict
    env.step('VERDICT', LABEL)
    assert env.state.done


def test_cached_output_cannot_exceed_smaller_budget(tmp_path):
    client = Client(ModelConfig('fixture'), tmp_path/'cache', tmp_path/'audit', FixtureTransport())
    executor = LLMExecutor(client)
    env = CourtroomEnv(executor)
    env.reset(ModelInput('', '', TEXT))
    env.step('ACCUSE', LABEL)
    small = CourtroomEnv(executor, Budget(max_tokens=1))
    small.reset(ModelInput('', '', TEXT))
    small.step('ACCUSE', LABEL)
    assert small.state.calls == small.state.input_tokens == small.state.output_tokens == 0
    assert small.state.forced_verdict


def test_fixed_baseline_obeys_call_budget(tmp_path):
    client = Client(ModelConfig('fixture'), tmp_path/'cache', tmp_path/'audit', FixtureTransport())
    with pytest.raises(BudgetExhausted):
        run_fixed(client,ModelInput('', '', TEXT),'sample',Budget(max_calls=1))
    assert client.transport.calls == 1


def test_model_snapshot_changes_when_environment_model_changes(monkeypatch):
    from src.courtroom_rl.runner import resolved_model
    config = {'model':{'name_env':'NVIDIA_MODEL','base_url_env':'NVIDIA_BASE_URL','api_key_env':'NVIDIA_API_KEY'}}
    monkeypatch.setenv('NVIDIA_API_KEY','not-a-real-key')
    monkeypatch.setenv('NVIDIA_MODEL','model-A')
    monkeypatch.setenv('NVIDIA_BASE_URL','https://integrate.api.nvidia.com/v1')
    a = resolved_model(config,False)
    monkeypatch.setenv('NVIDIA_MODEL','model-B')
    assert resolved_model(config,False) != a


def test_failed_heuristic_preparation_charges_attempt_and_replays(tmp_path):
    from src.courtroom_rl.runner import episode
    from src.courtroom_rl.data import Case
    from src.courtroom_rl.replay import replay
    import random
    class BadTransport(FixtureTransport):
        def complete(self,payload):
            r = super().complete(payload)
            obj = json.loads(r['choices'][0]['message']['content'])
            obj['evidence_ids'] = ['T999']
            r['choices'][0]['message']['content'] = json.dumps(obj)
            return r
    client = Client(ModelConfig('fixture',max_attempts=2,backoff_seconds=0),tmp_path/'cache',tmp_path/'audit',BadTransport())
    case = Case('sample',1,'train',ModelInput('', '', TEXT),LABEL)
    config = {'budget':{'max_calls':1},'reward':{}}
    env,_ = episode(case,config,LLMExecutor(client),'heuristic',random.Random(0))
    assert env.state.calls == 1 and env.state.input_tokens == 25
    assert env.trace[0]['budget_blocked']
    assert replay(case.input,env.trace,Budget(max_calls=1)).public_state() == env.public_state()


def test_runner_single_baseline_fixture(tmp_path):
    main(['smoke','--fixture','--policy','single','--output',str(tmp_path/'single')])
    report = json.loads((tmp_path/'single/summary.json').read_text())
    assert report['successful'] == 1


def test_token_usage_includes_rejected_attempt_before_next_request(tmp_path):
    from src.courtroom_rl.executor import AccountingTransport
    class UsageTransport:
        def complete(self,payload):
            return {'usage':{'prompt_tokens':100,'completion_tokens':100}}
    counted = AccountingTransport(UsageTransport())
    counted.limits = (5,300)
    counted.complete({'messages':[],'max_completion_tokens':50})
    with pytest.raises(BudgetExhausted):
        counted.complete({'messages':[],'max_completion_tokens':50})
    assert counted.calls == 1


def test_single_baseline_reports_all_retry_costs(tmp_path, monkeypatch):
    import src.courtroom_rl.runner as runner
    from src.courtroom_rl.data import Case
    class Retry(FixtureTransport):
        def __init__(self):
            self.count = 0
        def complete(self,payload):
            self.count += 1
            response = super().complete(payload)
            if self.count == 1:
                response['choices'][0]['finish_reason'] = 'length'
            return response
    client = Client(ModelConfig('fixture',max_attempts=2,backoff_seconds=0),tmp_path/'cache',tmp_path/'audit',Retry())
    monkeypatch.setattr(runner,'create_client',lambda *args:client)
    case = Case('sample',1,'train',ModelInput('', '', TEXT),LABEL)
    summary = runner.evaluate([case],{'budget':{'max_calls':8,'max_tokens':24000}},tmp_path,True,'single')
    assert summary['calls']['mean'] == 2
    assert summary['tokens']['mean'] == 100


def test_timeout_reserves_unknown_token_usage():
    class TimeoutTransport:
        def complete(self,payload):
            raise TimeoutError('No provider usage available')
    counted = AccountingTransport(TimeoutTransport())
    with pytest.raises(TimeoutError):
        counted.complete({'messages':[],'max_completion_tokens':50})
    assert counted.calls == counted.estimated_usage_calls == 1
    assert counted.input_tokens >= 128 and counted.output_tokens == 50


def test_missing_usage_is_preserved_across_cache_hits(tmp_path):
    class MissingUsage(FixtureTransport):
        def complete(self,payload):
            result = super().complete(payload)
            result.pop('usage')
            return result
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',MissingUsage())
    executor = LLMExecutor(client)
    first = CourtroomEnv(executor)
    first.reset(ModelInput('', '', TEXT))
    first.step('ACCUSE',LABEL)
    cached = CourtroomEnv(executor)
    cached.reset(ModelInput('', '', TEXT))
    cached.step('ACCUSE',LABEL)
    assert cached.state.input_tokens == first.state.input_tokens > 0
    assert cached.state.output_tokens == first.state.output_tokens > 0
    assert cached.state.estimated_usage_calls == first.state.estimated_usage_calls == 1
    small = CourtroomEnv(executor,Budget(max_tokens=1))
    small.reset(ModelInput('', '', TEXT))
    small.step('ACCUSE',LABEL)
    assert small.state.calls == 0 and small.state.forced_verdict
