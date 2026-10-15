"""Single-contract action schemas; baseline grounding/taxonomy/client reused."""
from dataclasses import asdict
import json
import re

from src.labels import FALLACIES
from src.schemas import object_schema
from src.io_utils import digest
from src.courtroom_rl.schemas import Execution
from src.courtroom_rl.executor import wrap_accounting, BudgetExhausted
from src.courtroom_rl.evidence import passages_for, evidence_schema, resolve_references
from src.courtroom_rl.action_centric import ledger
from src.courtroom_rl.action_centric.prompts import role_behavior


def _base_contract(state,action,budget):
    passages=passages_for(state.case_input,target_only=action in ('TOP3_INIT','REVISE','PROPOSE_ALTERNATIVE','VERDICT'))
    grounded={'evidence_ids':evidence_schema(passages),'mechanism':{'type':'string','minLength':1,'maxLength':2000}}
    label={'type':'string','enum':list(FALLACIES)}
    if action=='TOP3_INIT':
        item=object_schema({'label':label,'claims':{'type':'array','minItems':1,'maxItems':min(budget.max_initial_claims_per_hypothesis,max(1,budget.max_claims//3)),
            'items':object_schema(grounded)}})
        schema=object_schema({'hypotheses':{'type':'array','minItems':3,'maxItems':3,'items':item}})
    elif action=='VERDICT':schema=object_schema({'label':label,**grounded})
    elif action in ('SUPPORT','CHALLENGE'):
        schema=object_schema({'claim_id':{'type':'string','enum':ledger.eligible(state,action)},**grounded})
    elif action=='CONCEDE':
        schema=object_schema({'claim_id':{'type':'string','enum':ledger.eligible(state,action)},'reason':{'type':'string','minLength':1}})
    elif action=='REVISE':
        schema=object_schema({'hypothesis_id':{'type':'string','enum':ledger.eligible(state,action)},'label':label,**grounded})
    elif action=='PROPOSE_ALTERNATIVE':
        schema=object_schema({'label':{'anyOf':[{'type':'string','enum':[l for l in FALLACIES if l not in [h.label for h in state.hypotheses]]},{'type':'null'}]},
            'no_op':{'type':'boolean'},**grounded})
        schema['properties']['evidence_ids']=evidence_schema(passages,allow_empty=True)
    else:raise ValueError('No LLM contract for action')
    return schema,passages


def contract(state,action,budget):
    schema,passages=_base_contract(state,action,budget)
    if action in ('SUPPORT','CHALLENGE','CONCEDE','REVISE'):
        target=getattr(state,'actor_target',None)
        if target not in ledger.eligible(state,action):raise ValueError('Illegal actor target')
        key='hypothesis_id' if action=='REVISE' else 'claim_id'
        schema['properties'][key]['enum']=[target]
    return schema,passages


INSTRUCTIONS={
    'TOP3_INIT':'Select exactly three distinct candidate labels, ranked by fit. Give concise source-grounded supporting claims for each; obey the claim-count limit in the schema. Do not return a final verdict.',
    'SUPPORT':'Select an eligible disputed claim and provide a substantive grounded response to its criticism. Do not simply repeat its existing explanation.',
    'REVISE':'Select a hypothesis to revise. Choose the label yourself and explain a genuinely new grounded distinction. You may retain or change its label.',
    'CHALLENGE':'Select an eligible existing claim to scrutinize. Explain a specific boundary violation, missing inference or source-supported charitable interpretation. This action critiques an existing claim, rather than proposing a new label.',
    'PROPOSE_ALTERNATIVE':'Propose a substantiated label from allowed_labels, never an existing label. If none is justified, return label=null, no_op=true, evidence_ids=[] and explain why. A no-op does not add a hypothesis. Never fill an arbitrary unused label just to satisfy this action.',
    'CONCEDE':'Select an eligible opposing claim and explain the concession. This is your position in the dialogue, not a declaration of ground-truth correctness.',
    'VERDICT':'Weigh all source evidence and arguments. Independently choose the single best label from ALL EIGHT classes, even outside the hypothesis pool. Give concise grounded reasoning. Never just copy an earlier label.',
}


def _public_event(event):
    result={k:event[k] for k in ('role','action','target','actor_target','invalid','no_op','budget_blocked') if k in event}
    payload=event.get('payload',{})
    result['payload']={k:payload[k] for k in ('claim_id','hypothesis_id','label','evidence_ids','mechanism','reason','no_op') if k in payload}
    if 'evidence_spans' in payload:
        result['payload']['evidence_spans']=[{k:span[k] for k in ('id','source','start','end','quote') if k in span} for span in payload['evidence_spans']]
    return result


def public_view(state):
    return {'input':state.case_input.as_dict(),'hypotheses':[asdict(h) for h in state.hypotheses],
        'claims':[{'id':c.claim_id,'hypothesis_id':c.hypothesis_id,'label':c.label,'author':c.author,
            'proposition':c.proposition,'kind':c.kind,'status':c.status,
            'evidence_ids':[s['id'] for s in c.evidence_spans]} for c in state.claims],
        'pending_request':state.pending_request,'ledger_revision':state.revision,
        'argument_events':[_public_event(e) for e in state.argument_events]}


def output_guide(state,action,budget,schema):
    """Describe a result instance, not a JSON Schema that the model can copy."""
    claim={'evidence_ids':['<select one supplied evidence ID>'],'mechanism':'<your concise source-grounded explanation>'}
    if action=='TOP3_INIT':
        example={'hypotheses':[{'label':f'<distinct candidate label {i}>','claims':[claim.copy()]} for i in range(1,4)]}
    elif action=='VERDICT':example={'label':'<best label from allowed_labels>',**claim}
    elif action=='REVISE':example={'hypothesis_id':'<choose eligible hypothesis>','label':'<choose allowed label>',**claim}
    elif action=='CONCEDE':example={'claim_id':'<choose eligible claim>','reason':'<your reason for conceding>'}
    elif action=='PROPOSE_ALTERNATIVE':example={'label':'<choose unused allowed label>','no_op':False,**claim}
    else:example={'claim_id':'<choose eligible claim>',**claim}
    allowed=[l for l in FALLACIES if action!='PROPOSE_ALTERNATIVE' or l not in [h.label for h in state.hypotheses]]
    result={'output_example':example,'allowed_labels':allowed,
        'eligible_claim_ids':ledger.eligible(state,action) if action in ('SUPPORT','CHALLENGE','CONCEDE') else [],
        'eligible_hypothesis_ids':ledger.eligible(state,action) if action=='REVISE' else [],
        'required_output_fields':list(schema['properties']),
        'format_rules':'Replace every <placeholder>. Return the result object only, not this guide or a schema. Use no extra fields.',
        'evidence_rule':'Select 1 to 3 distinct supplied IDs per grounded claim; do not return all passages.'}
    if action=='TOP3_INIT':
        amount='EXACTLY ONE claim each (total 3 claims)' if budget.max_initial_claims_per_hypothesis==1 else 'one or two claims each'
        result['top3_rule']=f'Exactly 3 hypotheses with distinct labels; {amount}. No additional claims.'
    if action=='PROPOSE_ALTERNATIVE':
        result['existing_labels']=[h.label for h in state.hypotheses]
        result['no_op_example']={'label':None,'no_op':True,'evidence_ids':[],'mechanism':'<why no further alternative is justified>'}
    return result


def validate_reasoning_templates(value):
    if isinstance(value,dict):
        for key,child in value.items():
            if key in ('mechanism','reason') and isinstance(child,str) and re.search(r'<(?:your|why|choose|select|distinct|best|placeholder)\b[^>]*>',child,re.IGNORECASE):
                raise ValueError('Replace template placeholders with actual reasoning')
            validate_reasoning_templates(child)
    elif isinstance(value,list):
        for child in value:validate_reasoning_templates(child)


class LLMExecutor:
    prompt_version='courtroom-action-centric-v4-target-dialogue'

    def __init__(self,client,input_estimator=None):
        self.client=client;wrap_accounting(client)
        if input_estimator is not None:self.client.transport.input_estimator=input_estimator

    def initialize(self,state,budget):return self._ask(state,'TOP3_INIT',budget)

    def execute(self,state,action,budget):return self._ask(state,action,budget)

    def _ask(self,state,action,budget):
        schema,passages=contract(state,action,budget)
        transport=self.client.transport
        start=transport.calls,transport.input_tokens,transport.output_tokens,transport.estimated_usage_calls
        final=action=='VERDICT'
        remaining_calls=budget.max_calls-state.calls-(0 if final else 1)
        remaining_tokens=budget.max_tokens-state.input_tokens-state.output_tokens-(0 if final else budget.verdict_reserve_tokens)
        transport.limits=(transport.calls+remaining_calls,transport.input_tokens+transport.output_tokens+remaining_tokens)
        transport.minimum_output_tokens=384 if action=='TOP3_INIT' else 128
        transport.action_attempt=0;transport.progress_context=f'{state.active_role}.{action}'
        role='Prosecutor' if action=='TOP3_INIT' else state.active_role
        system=(role_behavior(role)+'\n'
            'The RL controller selects the action and existing target. Use exactly actor_target. You choose new labels and grounded reasoning. '
            'Perform only the requested action. Return exactly one JSON INSTANCE with the requested fields. '
            'Do not return a schema, the guide, Markdown, extra fields, quote text or offsets. '
            'Select supplied evidence IDs; code resolves exact original source spans. Keep each mechanism below 45 words.\n'+INSTRUCTIONS[action])
        def validate(value):
            validate_reasoning_templates(value)
            if action in ('SUPPORT','CHALLENGE','CONCEDE','REVISE'):
                key='hypothesis_id' if action=='REVISE' else 'claim_id'
                if value.get(key)!=getattr(state,'actor_target',None):raise ValueError('Executor substituted actor target')
            mechanism=value.get('mechanism',value.get('reason',''))
            if action=='TOP3_INIT':ledger.initialize(state,value,budget)
            elif action=='PROPOSE_ALTERNATIVE' and value.get('no_op'):
                if value['label'] is not None or value['evidence_ids'] or not mechanism.strip():
                    raise ValueError('A no-op requires label=null, evidence_ids=[] and an explanation')
            elif action not in ('CONCEDE',) and not value.get('no_op'):
                if action=='PROPOSE_ALTERNATIVE' and value['label'] is None:
                    raise ValueError('A real alternative requires an unused label, evidence and no_op=false')
                ledger.grounded(state,value,action in ('REVISE','PROPOSE_ALTERNATIVE','VERDICT'))
        guide=output_guide(state,action,budget,schema) or {}
        if action in ('SUPPORT','CHALLENGE','CONCEDE','REVISE'):
            key='hypothesis_id' if action=='REVISE' else 'claim_id'
            guide['actor_target']=getattr(state,'actor_target',None)
            guide['eligible_hypothesis_ids' if action=='REVISE' else 'eligible_claim_ids']=[guide['actor_target']]
            if 'output_example' in guide:guide['output_example'][key]=guide['actor_target']
        def retry_instruction(feedback):
            return ('Previous result was rejected: '+feedback+'\nReturn a corrected JSON RESULT, never a JSON Schema. '
                'Do not repeat the invalid fields or append explanations outside JSON. Do not change action. '
                'Obey these eligible choices and the exact result shape: '+json.dumps(guide,ensure_ascii=False))
        try:
            result=self.client.generate(system_prompt=system,
                user_prompt=json.dumps({**public_view(state),'action_type':action,'actor_target':getattr(state,'actor_target',None),'instruction':INSTRUCTIONS[action],
                    'evidence_passages':[{k:p[k] for k in ('id','source','text')} for p in passages],**guide},ensure_ascii=False),
                schema=schema,validator=validate,
                include_schema_in_prompt=False,allow_json_fences=True,
                retry_instruction=retry_instruction,retry_previous_response=True,result_envelopes=('output_example',),
                metadata={'sample_id':state.sample_id,'stage':'action_centric_'+action,'action_type':action,
                    'role':role,'ledger_revision':state.revision,'state_hash':digest(asdict(state)),
                    'prompt_version':self.prompt_version})
            calls=1 if result.stats.cache_hit else transport.calls-start[0]
            inp=result.stats.prompt_tokens if result.stats.cache_hit else transport.input_tokens-start[1]
            out=result.stats.completion_tokens if result.stats.cache_hit else transport.output_tokens-start[2]
            if calls>remaining_calls or inp+out>remaining_tokens:raise BudgetExhausted('Logical request exceeds remaining budget')
        except BudgetExhausted as exc:
            exc.execution=Execution(calls=transport.calls-start[0],input_tokens=transport.input_tokens-start[1],
                output_tokens=transport.output_tokens-start[2],estimated_usage_calls=transport.estimated_usage_calls-start[3])
            raise
        return Execution(result.output,calls,inp,out,digest(result.output),
            int(self.client.cache.last_usage_estimated) if result.stats.cache_hit else transport.estimated_usage_calls-start[3])


class FixtureExecutor:
    """Explicit fixture, exercises target selection without provider requests."""
    def initialize(self,state,budget):
        passages=passages_for(state.case_input,True)
        obj={'hypotheses':[{'label':label,'claims':[{'evidence_ids':[passages[0]['id']],
            'mechanism':f'Initial supporting reason {i}.'}]} for i,label in enumerate(FALLACIES[:3])]}
        return Execution(obj,1,40,60)

    def execute(self,state,action,budget):
        schema,passages=contract(state,action,budget)
        obj={}
        for key,prop in schema['properties'].items():
            if 'enum' in prop:obj[key]=prop['enum'][0]
        if 'evidence_ids' in schema['properties']:obj['evidence_ids']=[passages[0]['id']]
        if 'mechanism' in schema['properties']:obj['mechanism']=f'{action} reason at revision {state.revision}.'
        if action=='VERDICT':obj['label']=FALLACIES[-1]
        if action=='CONCEDE':obj['reason']='Fixture concession.'
        if action=='PROPOSE_ALTERNATIVE':obj['no_op']=False
        if action=='PROPOSE_ALTERNATIVE':obj['label']=next(l for l in FALLACIES if l not in [h.label for h in state.hypotheses])
        return Execution(obj,1,40,30)


dialogue_view=public_view
