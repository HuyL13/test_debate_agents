"""Candidate-keyed constrained verifier output; source checks remain code-owned."""
from copy import deepcopy
from core import invoke
from pipeline import MODEL, settings
from verify import PROMPT, validate_verification, decide


def canonicalize(raw):
    return {'assessments':[dict(candidate_id=key, **value) for key,value in raw['assessments'].items()]}


def verification_schema(candidates, units):
    ids=[u['id'] for u in units]
    base={
        'mapping_status':{'type':'string','enum':['valid','partial','invalid']},
        'mechanism':{'type':'string','enum':['present','partial','absent']},
        'author':{'type':'string','enum':['endorsed','challenged','reported','unclear']},
        'defect':{'type':'string','enum':['supported','uncertain','absent']},
        'reason_code':{'type':'string'},
        'centrality':{'type':'string','enum':['central','supporting','incidental']},
        'evidence':{'type':'array','items':{'type':'integer','enum':ids}},
        'reason':{'type':'string','minLength':1},
    }
    branches=[]
    rules=[
        ('warrant_misuse',dict(mapping_status=['valid'],mechanism=['present','partial'],author=['endorsed'],defect=['supported'])),
        ('legitimate_support',dict(mapping_status=['valid','partial'],mechanism=['present','partial'],defect=['absent'])),
        ('challenged_argument',dict(mapping_status=['valid','partial'],mechanism=['present','partial'],author=['challenged'])),
        ('reported_argument',dict(mapping_status=['valid','partial'],mechanism=['present','partial'],author=['reported'])),
        ('insufficient_context',dict(mapping_status=['valid','partial'],mechanism=['present','partial'],defect=['uncertain'])),
        ('mechanism_missing',dict(mechanism=['absent'],defect=['uncertain','absent'])),
        ('mapping_invalid',dict(mapping_status=['invalid'],mechanism=['partial'],defect=['uncertain','absent'])),
        ('mapping_invalid',dict(mapping_status=['invalid'],mechanism=['absent'],defect=['uncertain','absent'])),
    ]
    for code, restrictions in rules:
        props=deepcopy(base);props['reason_code']={'type':'string','const':code}
        for key,values in restrictions.items():props[key]['enum']=values
        if props['mechanism']['enum']!=['absent']:props['evidence']['minItems']=1
        branches.append({'type':'object','additionalProperties':False,'properties':props,'required':list(props)})
    assessments={c['id']:{'anyOf':deepcopy(branches)} for c in candidates}
    return {'type':'object','additionalProperties':False,'properties':{'assessments':{'type':'object','additionalProperties':False,'properties':assessments,'required':list(assessments)}},'required':['assessments']}


def request(sample_id,payload,version='v5-structured-verify',repeat=0):
    candidates=payload['candidates'];units=payload['units'];config=settings()
    config['response_format']={'type':'json_schema','json_schema':{'name':'candidate_assessments','strict':True,'schema':verification_schema(candidates,units)}}
    prompt=PROMPT+'\nOUTPUT FORMAT OVERRIDE: assessments must be an OBJECT keyed by the exact candidate IDs, not an array. Each value contains the assessment fields without candidate_id, plus centrality: central/supporting/incidental, describing its importance to the author\'s main conclusion. All source and consistency requirements still apply.'
    return invoke(MODEL,'verify',sample_id,prompt,payload,lambda raw: validate_verification(canonicalize(raw),candidates,units),version,repeat,config)
