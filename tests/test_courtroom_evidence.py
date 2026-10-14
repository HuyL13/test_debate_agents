import json

import pytest

from src.data.loader import ModelInput
from src.courtroom_rl.evidence import passages_for, evidence_schema, resolve_references
from src.courtroom_rl.executor import LLMExecutor
from src.courtroom_rl.env import CourtroomEnv
from src.courtroom_rl.baseline import FixtureTransport
from src.llm.client import Client
from src.llm.config import ModelConfig


def test_sentences_preserve_unicode_whitespace_and_repeated_offsets():
    case = ModelInput('Title.', 'Parent “quote”.', '  Same sentence!\n\tSame sentence!  Final — sentence.')
    passages = passages_for(case)
    assert [p['text'] for p in passages if p['source']=='comment'] == ['Same sentence!','Same sentence!','Final — sentence.']
    resolved = resolve_references({'evidence_ids':['T2','P1']},passages)
    assert resolved['evidence_spans'][0]['start'] == 18
    for span in resolved['evidence_spans']:
        assert getattr(case,span['source'])[span['start']:span['end']] == span['quote']
    assert resolved['supported_quote'] == 'Same sentence!'
    assert resolved['source'] == 'comment'


def test_target_only_schema_blocks_parent_and_fabricated_ids():
    passages = passages_for(ModelInput('Title.', 'Parent.', 'Target.'),target_only=True)
    schema = evidence_schema(passages)
    assert schema['items']['enum'] == ['T1']
    for ids in (['P1'],['T999'],['T1','T1'],[]):
        with pytest.raises(ValueError):
            resolve_references({'evidence_ids':ids},passages)


def test_disjoint_evidence_is_not_joined_into_a_fabricated_quote():
    passages = passages_for(ModelInput('', '', 'First premise. Unrelated text. Final conclusion.'))
    result = resolve_references({'evidence_ids':['T1','T3']},passages)
    assert [s['quote'] for s in result['evidence_spans']] == ['First premise.','Final conclusion.']
    assert result['supported_quote'] == 'First premise.'


def test_long_sentences_use_existing_passage_splitter_without_losing_text():
    text = ' '.join(f'word{i}' for i in range(130))
    passages = passages_for(ModelInput('', '', text),target_only=True)
    assert len(passages) > 1
    assert ' '.join(p['text'] for p in passages) == text


def test_executor_requests_ids_and_ledger_keeps_selected_offsets(tmp_path):
    class Recording(FixtureTransport):
        def complete(self,payload):
            self.payload = payload
            response = super().complete(payload)
            obj = json.loads(response['choices'][0]['message']['content'])
            obj['evidence_ids'] = ['T2']
            response['choices'][0]['message']['content'] = json.dumps(obj)
            return response
    transport = Recording()
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',transport)
    env = CourtroomEnv(LLMExecutor(client))
    env.reset(ModelInput('', '', 'Same sentence! Same sentence!'))
    env.step('ACCUSE','Appeal to Tradition')
    props = transport.payload['response_format']['json_schema']['schema']['properties']
    assert 'supported_quote' not in props and 'source' not in props
    assert 'evidence_ids' in props
    assert env.state.claims[0].source_span['start'] == 15
    assert env.state.claims[0].evidence_spans[0]['id'] == 'T2'


@pytest.mark.parametrize('action,role', [('ACCUSE','Prosecutor'),('CHALLENGE','Defender'),('DEFEND_CLAIM','Prosecutor')])
def test_rl_action_prompt_has_one_output_contract_without_baseline_fields(tmp_path,action,role):
    from src.courtroom_rl.executor import FixtureExecutor
    class Recording(FixtureTransport):
        def complete(self,payload):
            self.payload = payload
            return super().complete(payload)
    transport = Recording()
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',transport)
    env = CourtroomEnv(FixtureExecutor())
    env.reset(ModelInput('', '', 'Old practice. Therefore this is best.'))
    if action != 'ACCUSE':
        env.step('ACCUSE','Appeal to Tradition')
    env.state.active_role = role
    LLMExecutor(client).execute(env.state,action,'Appeal to Tradition' if action == 'ACCUSE' else 'C1',env.budget)
    system = transport.payload['messages'][0]['content']
    for legacy in ('has_fallacy_charge','candidate_class','concede_charge','alternative_class','supporting_quote'):
        assert legacy not in system
    user = json.loads(transport.payload['messages'][1]['content'])
    example = user['output_example']
    schema = transport.payload['response_format']['json_schema']['schema']
    assert set(example) == set(schema['properties'])
    assert example['label'] == 'Appeal to Tradition'
    assert example['attacks_claim_ids'] == (['C1'] if action == 'CHALLENGE' else [])
    assert 'BENCHMARK FALLACY' in system


def test_empty_target_does_not_fall_back_to_parent_evidence():
    with pytest.raises(ValueError,match='target'):
        passages_for(ModelInput('Title.', 'Parent.', '  '),target_only=True)


def test_fixed_baseline_restores_original_reports_and_records_source(tmp_path):
    from src.courtroom_rl.baseline import run_fixed
    class ContextDefense(FixtureTransport):
        def complete(self,payload):
            response = super().complete(payload)
            obj = json.loads(response['choices'][0]['message']['content'])
            if 'concede_charge' in obj:
                obj['concede_charge'] = False
                obj['alternative_class'] = 'Appeal to Nature'
                obj['evidence_ids'] = ['P1']
            response['choices'][0]['message']['content'] = json.dumps(obj)
            return response
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',ContextDefense())
    result = run_fixed(client,ModelInput('Title.','Parent evidence.','Target evidence.'),'sample')
    assert result['reports']['Defender']['counter_quote'] == 'Parent evidence.'
    assert 'evidence_ids' not in result['reports']['Defender']
    assert result['evidence_resolutions']['Defender'][0]['source'] == 'parent_comment'


def test_original_baseline_remains_available_without_id_adapter(tmp_path):
    from src.courtroom_rl.baseline import run_fixed
    class Recording(FixtureTransport):
        def complete(self,payload):
            props = payload['response_format']['json_schema']['schema']['properties']
            assert 'evidence_ids' not in props
            return super().complete(payload)
    client = Client(ModelConfig('fixture'),tmp_path/'cache',tmp_path/'audit',Recording())
    result = run_fixed(client,ModelInput('', '', 'Target evidence.'),'sample',evidence_refs=False)
    assert result['calls'] == 3


def test_ledger_rejects_forged_ids_and_mismatched_compatibility_quote():
    from src.courtroom_rl.ledger import validate_payload
    from src.courtroom_rl.executor import FixtureExecutor
    env = CourtroomEnv(FixtureExecutor())
    env.reset(ModelInput('', 'Parent.', 'First. Second.'))
    passages = passages_for(env.state.case_input,target_only=True)
    raw = {'label':'Appeal to Tradition','evidence_ids':['T1'],'mechanism':'Reason.',
           'attacks_claim_ids':[],'answer_to_pending_request':''}
    resolved = resolve_references(raw,passages)
    forged = {**resolved,'evidence_ids':['P999'],'evidence_spans':[{**resolved['evidence_spans'][0],'id':'P999'}]}
    for payload in (forged,{**resolved,'supported_quote':'Second.'}):
        with pytest.raises(ValueError):
            validate_payload(payload,env.state,'ACCUSE','Appeal to Tradition')


def test_new_secondary_evidence_counts_for_revision_and_duplicate_identity():
    from src.courtroom_rl.ledger import validate_payload,insert_claim
    from src.courtroom_rl.executor import FixtureExecutor
    env = CourtroomEnv(FixtureExecutor())
    env.reset(ModelInput('', '', 'First premise. Old premise. New premise.'))
    passages = passages_for(env.state.case_input,target_only=True)
    base = {'label':'Appeal to Tradition','mechanism':'Same reasoning.',
            'attacks_claim_ids':[],'answer_to_pending_request':''}
    first = resolve_references({**base,'evidence_ids':['T1','T2']},passages)
    second = resolve_references({**base,'evidence_ids':['T1','T3']},passages)
    a = insert_claim(env.state,'ACCUSE',first)
    b = insert_claim(env.state,'ACCUSE',second)
    assert a.normalized_fingerprint != b.normalized_fingerprint
    revision = {**second,'label':'False Dilemma'}
    # The earlier identical evidence exists only in the second claim; remove it
    # to verify the new secondary premise is sufficient for admission.
    env.state.claims.pop()
    validate_payload(revision,env.state,'REVISE_CHARGE','False Dilemma')
