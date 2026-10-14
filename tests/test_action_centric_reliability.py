import json
from copy import deepcopy
from dataclasses import replace
import pytest

from src.llm.client import Client
from src.llm.config import ModelConfig
from src.schemas import object_schema
from src.courtroom_rl.executor import AccountingTransport, BudgetExhausted
from src.courtroom_rl.action_centric.executor import LLMExecutor, FixtureExecutor
from src.courtroom_rl.action_centric.env import CourtroomEnv, Budget
from tests.test_action_centric import CASE


class ResponseTransport:
    def __init__(self,outputs,usage=None):self.outputs=list(outputs);self.requests=[];self.usage=usage
    def complete(self,payload):
        self.requests.append(deepcopy(payload))
        result={'choices':[{'message':{'content':self.outputs.pop(0)},'finish_reason':'stop'}]}
        if self.usage is not None:result['usage']=self.usage
        return result


def test_token_count_admits_prompt_that_byte_bound_wrongly_blocks():
    response=ResponseTransport(['{}'],{'prompt_tokens':1800,'completion_tokens':100})
    counted=AccountingTransport(response,input_estimator=lambda payload:2000)
    counted.limits=(2,4500)
    counted.complete({'messages':[{'role':'user','content':'abcd '*2500}],'max_completion_tokens':1600})
    assert counted.calls==1 and counted.input_tokens==1800
    assert response.requests[0]['max_completion_tokens']==1600


def test_actual_usage_overrun_is_counted_and_not_accepted_as_valid():
    response=ResponseTransport(['{}'],{'prompt_tokens':2500,'completion_tokens':100})
    counted=AccountingTransport(response,input_estimator=lambda payload:2000)
    counted.limits=(1,2500)
    with pytest.raises(BudgetExhausted,match='reported usage'):
        counted.complete({'messages':[],'max_completion_tokens':300})
    assert counted.calls==1 and counted.input_tokens+counted.output_tokens==2600


def test_client_can_omit_schema_from_json_object_prompt_without_disabling_validation(tmp_path):
    transport=ResponseTransport(['{"ok":true}'],{'prompt_tokens':20,'completion_tokens':10})
    c=Client(ModelConfig('fixture',structured_output=False),tmp_path/'cache',tmp_path/'audit',transport)
    schema=object_schema({'ok':{'type':'boolean'}})
    out=c.generate(system_prompt='Return a JSON object.',user_prompt='Example: {"ok":true}',schema=schema,
        metadata={'stage':'action_centric_test'},include_schema_in_prompt=False)
    assert out.output=={'ok':True}
    assert 'JSON schema:' not in transport.requests[0]['messages'][0]['content']
    assert transport.requests[0]['response_format']=={'type':'json_object'}


def test_safe_fence_handling_never_accepts_extra_objects_or_fields(tmp_path):
    schema=object_schema({'ok':{'type':'boolean'}})
    for index,raw in enumerate(['```json\n{"ok":true}\n```','{"ok":true}\n{"extra":1}','{"ok":true,"extra":1}']):
        transport=ResponseTransport([raw],{'prompt_tokens':20,'completion_tokens':10})
        c=Client(ModelConfig('fixture',max_attempts=1),tmp_path/f'cache{index}',tmp_path/f'audit{index}',transport)
        if index:
            with pytest.raises(ValueError):
                c.generate(system_prompt='JSON',user_prompt='JSON',schema=schema,metadata={},allow_json_fences=True)
        else:
            assert c.generate(system_prompt='JSON',user_prompt='JSON',schema=schema,metadata={},allow_json_fences=True).output=={'ok':True}


def test_v3_retry_sees_previous_error_and_dynamic_allowed_labels(tmp_path):
    e=CourtroomEnv(FixtureExecutor());e.reset(CASE)
    wrong={'label':e.state.hypotheses[0].label,'no_op':False,'evidence_ids':['T1'],'mechanism':'Invalid repeated label.'}
    valid={'label':None,'no_op':True,'evidence_ids':[],'mechanism':'No additional class is justified.'}
    transport=ResponseTransport([json.dumps(wrong),json.dumps(valid)],{'prompt_tokens':20,'completion_tokens':10})
    c=Client(ModelConfig('fixture',structured_output=False,max_attempts=2,backoff_seconds=0),tmp_path/'cache',tmp_path/'audit',transport)
    result=LLMExecutor(c).execute(e.state,'PROPOSE_ALTERNATIVE',Budget(max_tokens=100000))
    assert result.payload['no_op'] and result.payload['label'] is None and result.calls==2
    first=transport.requests[0];user=json.loads(first['messages'][1]['content'])
    assert 'output_example' in user and 'allowed_labels' in user
    assert wrong['label'] not in user['allowed_labels']
    assert not any('JSON schema:' in m['content'] for m in first['messages'])
    second=transport.requests[1]
    assert any(m['role']=='assistant' and m['content']==json.dumps(wrong) for m in second['messages'])
    assert 'allowed_labels' in second['messages'][-1]['content']


def test_invalid_mixed_noop_is_not_accepted(tmp_path):
    e=CourtroomEnv(FixtureExecutor());e.reset(CASE)
    raw=json.dumps({'label':None,'no_op':False,'evidence_ids':[],'mechanism':'Missing a real proposal.'})
    transport=ResponseTransport([raw],{'prompt_tokens':20,'completion_tokens':10})
    c=Client(ModelConfig('fixture',max_attempts=1),tmp_path/'cache',tmp_path/'audit',transport)
    with pytest.raises(ValueError):
        LLMExecutor(c).execute(e.state,'PROPOSE_ALTERNATIVE',Budget(max_tokens=100000))


def test_single_result_wrapper_keeps_inner_validation_and_rejects_siblings(tmp_path):
    schema=object_schema({'ok':{'type':'boolean'}})
    raws=['{"output_example":{"ok":true}}','{"output_example":{"ok":true,"extra":1}}',
          '{"output_example":{"ok":true},"notes":"ignored?"}']
    for index,raw in enumerate(raws):
        c=Client(ModelConfig('fixture',max_attempts=1),tmp_path/f'cache{index}',tmp_path/f'audit{index}',
            ResponseTransport([raw],{'prompt_tokens':20,'completion_tokens':10}))
        kwargs=dict(system_prompt='JSON',user_prompt='JSON',schema=schema,metadata={},result_envelopes=('output_example',))
        if index:
            with pytest.raises(ValueError):c.generate(**kwargs)
        else:
            assert c.generate(**kwargs).output=={'ok':True}
            assert json.loads((tmp_path/f'audit{index}').read_text())['normalizations']==['single_result_envelope:output_example']


def test_arrow_reasoning_is_not_a_template_placeholder(tmp_path):
    e=CourtroomEnv(FixtureExecutor());e.reset(CASE)
    raw=json.dumps({'claim_id':'C1','evidence_ids':['T1'],'mechanism':'The proposed inference A -> B lacks a causal warrant.'})
    c=Client(ModelConfig('fixture',max_attempts=1),tmp_path/'cache',tmp_path/'audit',
        ResponseTransport([raw],{'prompt_tokens':20,'completion_tokens':10}))
    assert '->' in LLMExecutor(c).execute(e.state,'CHALLENGE',Budget(max_tokens=100000)).payload['mechanism']


def test_nested_top3_template_reasoning_is_rejected(tmp_path):
    e=CourtroomEnv(FixtureExecutor());e.reset(CASE)
    raw=deepcopy(e.initialization['execution']['payload'])
    raw['hypotheses'][1]['claims'][0]['mechanism']='<your concise source-grounded explanation>'
    c=Client(ModelConfig('fixture',max_attempts=1),tmp_path/'cache',tmp_path/'audit',
        ResponseTransport([json.dumps(raw)],{'prompt_tokens':20,'completion_tokens':10}))
    from src.courtroom_rl.action_centric.state import State
    with pytest.raises(ValueError,match='placeholder'):
        LLMExecutor(c).initialize(State(CASE),Budget(max_tokens=100000))


def test_token_counter_includes_schema_and_checks_artifact_hash(tmp_path):
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from src.io_utils import file_hash
    from src.courtroom_rl.action_centric.token_count import Llama3TokenCounter
    tokenizer=Tokenizer(WordLevel({'[UNK]':0},unk_token='[UNK]'));tokenizer.pre_tokenizer=Whitespace()
    path=tmp_path/'tokenizer.json';tokenizer.save(str(path))
    counter=Llama3TokenCounter(path,file_hash(path))
    small={'messages':[{'role':'user','content':'Hello'}]}
    big={**small,'response_format':{'type':'json_schema','json_schema':{'schema':{'description':'long '*1000}}}}
    assert counter(big)>counter(small)+500
    with pytest.raises(ValueError,match='checksum'):Llama3TokenCounter(path,'wrong')
