import json
from dataclasses import asdict

from src.courtroom_rl.vendor.baseline.adversarial_debate import execute
from src.courtroom_rl.vendor.baseline.adversarial_prompts import adversarial_system_prompt
from src.courtroom_rl.executor import AccountingTransport, BudgetExhausted, wrap_accounting
from src.courtroom_rl.schemas import Budget
from src.labels import FALLACIES
from src.courtroom_rl.evidence import passages_for, evidence_schema, resolve_references


def run_fixed(client, model_input, sample_id, budget=None, evidence_refs=True):
    """Original one-pass routing; optional ID-to-quote adapter for grounding."""
    reports, usage, cached_estimates, evidence_resolutions = {}, [], [], {}
    wrap_accounting(client)
    transport = client.transport
    budget = budget or Budget()
    start = transport.calls, transport.input_tokens, transport.output_tokens, transport.estimated_usage_calls
    transport.limits = (transport.calls+budget.max_calls,transport.input_tokens+transport.output_tokens+budget.max_tokens)

    def ask(role, stage, workspace, history, instruction, schema, validator):
        if len(reports) >= budget.max_decisions:
            raise BudgetExhausted('Fixed baseline cannot finish within matched decision cap')
        quote_field = 'quote' if 'quote' in schema['properties'] else 'counter_quote' if 'counter_quote' in schema['properties'] else None
        passages = passages_for(model_input,target_only=role=='Prosecutor') if evidence_refs and quote_field else None
        prompt = adversarial_system_prompt(role, 'classification')
        user = {'input':model_input.as_dict(),'workspace':workspace,'history':history,'instruction':instruction}
        original_validator = validator
        if passages is not None:
            from copy import deepcopy
            schema = deepcopy(schema)
            del schema['properties'][quote_field]
            schema['properties']['evidence_ids'] = evidence_schema(passages,allow_empty=role=='Defender',max_items=1)
            schema['required'] = ['evidence_ids' if k == quote_field else k for k in schema['required']]
            prompt += '\nEVIDENCE FORMAT OVERRIDE: Select evidence_ids from supplied passages instead of generating quote text. Defender may select no evidence only when conceding. Return the supplied schema.'
            user['evidence_passages'] = passages

            def restore(value):
                resolved = resolve_references(value,passages,allow_empty=role=='Defender' and value.get('concede_charge') is True,max_items=1)
                return {**{k:v for k,v in value.items() if k != 'evidence_ids'},quote_field:resolved['supported_quote']}

            validator = lambda value:original_validator(restore(value))
        result = client.generate(
            system_prompt=prompt,
            user_prompt=json.dumps(user,ensure_ascii=False),
            schema=schema, validator=validator,
            metadata={'sample_id': sample_id, 'stage': stage,
                      'baseline': 'fixed_adversarial_evidence_v2' if evidence_refs else 'fixed_adversarial_original'},
        )
        logical_calls = transport.calls-start[0]+sum(int(x.cache_hit) for x in usage)
        logical_tokens = transport.input_tokens+transport.output_tokens-start[1]-start[2]+sum(x.total_tokens for x in usage if x.cache_hit)
        if result.stats.cache_hit:
            logical_calls += 1
            logical_tokens += result.stats.total_tokens
        if logical_calls > budget.max_calls or logical_tokens > budget.max_tokens:
            raise BudgetExhausted('Fixed baseline exceeds matched logical budget')
        # Reserve cached logical usage in subsequent physical admission limits.
        if result.stats.cache_hit:
            calls_cap,tokens_cap = transport.limits
            transport.limits = (calls_cap-1,tokens_cap-result.stats.total_tokens)
        output = restore(result.output) if passages is not None else result.output
        if passages is not None:
            evidence_resolutions[role] = resolve_references(result.output,passages,
                allow_empty=role=='Defender' and result.output.get('concede_charge') is True,max_items=1)['evidence_spans']
        reports[role] = output
        usage.append(result.stats)
        cached_estimates.append(int(result.stats.cache_hit and client.cache.last_usage_estimated))
        return output

    _, _, verdict, stop = execute(ask, model_input, 'classification')
    return {'prediction': verdict['prediction'], 'stop_reason': stop, 'reports': reports,
            'evidence_resolutions':evidence_resolutions,
            'calls': transport.calls-start[0]+sum(int(x.cache_hit) for x in usage),
            'input_tokens': transport.input_tokens-start[1]+sum(x.prompt_tokens for x in usage if x.cache_hit),
            'output_tokens': transport.output_tokens-start[2]+sum(x.completion_tokens for x in usage if x.cache_hit),
            'estimated_usage_calls':transport.estimated_usage_calls-start[3]+sum(cached_estimates)}


class FixtureTransport:
    """Schema-aware deterministic fixture; no claim of LLM performance."""
    def complete(self, payload):
        props = payload['response_format']['json_schema']['schema']['properties']
        user = json.loads(payload['messages'][1]['content'])
        if 'evidence_ids' in props and 'mechanism' in props:
            obj = {'label':user['selected_label'],'evidence_ids':[props['evidence_ids']['items']['enum'][0]],
                   'mechanism':'Fixture reasoning for '+user['action'],
                   'attacks_claim_ids':user['required_attacks'],
                   'answer_to_pending_request':props['answer_to_pending_request']['enum'][0]}
        elif 'supported_quote' in props:
            state = user['state']
            obj = {'label': user['selected_label'], 'supported_quote': state['case_input']['comment'][:100],
                   'source': 'comment', 'mechanism': 'Fixture reasoning for '+user['action'],
                   'attacks_claim_ids': user['required_attacks'],
                   'answer_to_pending_request': props['answer_to_pending_request']['enum'][0]}
        elif 'has_fallacy_charge' in props:
            obj = {'has_fallacy_charge': True, 'candidate_class': FALLACIES[0],
                   'quote': user['input']['comment'][:100], 'defect_mechanism': 'Fixture defect.'}
        elif 'concede_charge' in props:
            obj = {'concede_charge': True, 'alternative_class': 'None',
                   'charitable_interpretation': 'Fixture concession.', 'counter_quote': ''}
        elif 'label' in props:
            obj = {'label':FALLACIES[0], 'reason':'Fixture classification.'}
        else:
            obj = {'prediction': FALLACIES[0], 'confidence': .5, 'content': 'Fixture verdict.'}
        if 'evidence_ids' in props and 'evidence_ids' not in obj:
            obj.pop('quote',None)
            obj.pop('counter_quote',None)
            obj['evidence_ids'] = [] if obj.get('concede_charge') else [props['evidence_ids']['items']['enum'][0]]
        return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(obj)}}],
                'model': 'fixture', 'usage': {'prompt_tokens':25, 'completion_tokens':25, 'total_tokens':50}}
