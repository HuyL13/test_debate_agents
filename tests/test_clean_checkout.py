import json
from pathlib import Path

import pytest

from src.data.loader import ModelInput


@pytest.mark.parametrize('policy',['adversarial'])
def test_clean_dialectical_policies_run_offline(policy,tmp_path):
    from src.engine import Engine
    from src.llm.client import Client,ModelConfig
    client=Client(ModelConfig(provider='mock',name='offline-fixture'),tmp_path/'cache.sqlite3',tmp_path/'calls.jsonl')
    result=Engine(client,task='classification',mode='adaptive',adaptive_policy=policy,use_patterns=True).run(
        ModelInput('Title','','We have always done this, so we should continue.'),{})
    assert result['framework']=='adversarial'
    assert result['prosecutor'] and result['defender'] and result['arbiter']['prediction']==result['prediction']


def test_clean_package_has_explicit_policy_modules():
    from src.dialectical import debate
    from src.baseline.single import system_prompt
    assert callable(debate.execute)
    assert 'Hasty Generalization' in system_prompt('classification',True)


@pytest.mark.parametrize('mode,policy',[('adaptive','ars_review'),('adaptive','planner'),('fixed','adversarial'),
    ('adaptive','adversarial_balanced'),('adaptive','adversarial_guarded')])
def test_obsolete_flows_are_not_silently_accepted(mode,policy):
    from src.engine import Engine
    with pytest.raises(ValueError):Engine(None,task='classification',mode=mode,adaptive_policy=policy)


def test_cli_accepts_model_override_of_placeholder(monkeypatch):
    from src.runner import cli
    seen=[]
    monkeypatch.setattr('src.runner.execute',lambda config,**kwargs:seen.append(config) or {'status':'complete'})
    monkeypatch.setattr('sys.argv',['run_classification','--model','example-model'])
    assert cli('classification')==0
    assert seen[0]['model']['name']=='example-model'
