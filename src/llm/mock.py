"""Deterministic dialectical plumbing fixtures, never benchmark predictions."""
import json
from src.io_utils import digest


class MockTransport:
    def complete(self,payload):
        schema=payload['response_format']['json_schema']['schema'];props=schema['properties']
        user=json.loads(payload['messages'][1]['content']);comment=user.get('input',{}).get('comment','')
        seed=int(digest(user.get('input',user))[:8],16);quote=comment[:220]
        def fixture(s):
            if 'enum' in s:return s['enum'][0]
            if s.get('type')=='object':return {k:fixture(v) for k,v in s.get('properties',{}).items() if k in s.get('required',[])}
            if s.get('type')=='boolean':return False
            if s.get('type') in ('number','integer'):return s.get('minimum',0)
            if s.get('type')=='array':return []
            return 'OFFLINE MOCK fixture.'
        value=fixture(schema)
        if 'has_fallacy_charge' in props:
            labels=props['candidate_class']['enum'];cand=labels[seed%len(labels)]
            value.update(has_fallacy_charge=cand!='None',candidate_class=cand,defect_mechanism='OFFLINE MOCK defect.',quote=quote if cand!='None' else '')
            if 'runner_up_class' in props:
                value.update(runner_up_class=next(l for l in props['runner_up_class']['enum'] if l!=cand),
                    runner_up_defect='OFFLINE MOCK alternative.',runner_up_quote=quote)
        elif 'concede_charge' in props:
            value.update(concede_charge=True,charitable_interpretation='OFFLINE MOCK agreement.',counter_quote=quote)
            if 'alternative_class' in props:value['alternative_class']='None'
            for k in ['primary_failure','counter_quote','alternative_premise','alternative_conclusion','alternative_inference','decisive_comparison']:
                if k in props and 'primary_assessment' in props:value[k]=''
        elif 'prediction' in props:
            labels=props['prediction']['enum'];value.update(prediction=labels[seed%len(labels)],confidence=.9,
                content='OFFLINE MOCK: deterministic plumbing fixture, not model analysis.')
            if 'assessments' in props:
                for assessment in value['assessments'].values():assessment.update(score=80,reason='OFFLINE MOCK fit.')
        return dict(id='mock-'+digest(payload)[:12],model='offline-mock-v1',
            choices=[dict(finish_reason='stop',message=dict(content=json.dumps(value),refusal=None))],
            usage=dict(prompt_tokens=0,completion_tokens=0,total_tokens=0))
