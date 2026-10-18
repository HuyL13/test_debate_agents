from copy import deepcopy
from core import OPERATORS,STANCES,COMMITMENTS,SCOPES,ALTERNATIVES,require,validate_extraction


def extraction_schema(units):
    ids=[u['id'] for u in units]
    conclusions=[u['id'] for u in units if u['source']!='title']
    branches=[]
    for cid in conclusions:
        premises=[i for i in ids if i!=cid]
        if not premises:continue
        properties={
          'premises':{'type':'array','minItems':1,'maxItems':len(premises),'items':{'type':'integer','enum':premises}},
          'conclusion':{'type':'integer','const':cid},
          'operator':{'type':'string','enum':OPERATORS},
          'stance':{'type':'string','enum':STANCES},
          'commitment':{'type':'string','enum':COMMITMENTS},
          'scope_change':{'type':'string','enum':SCOPES},
          'alternatives':{'type':'string','enum':ALTERNATIVES},
          'chain':{'anyOf':[{'type':'array','maxItems':0,'items':{'type':'integer','enum':ids}},{'type':'array','minItems':2,'maxItems':len(ids),'items':{'type':'integer','enum':ids}}]}}
        branches.append({'type':'object','additionalProperties':False,'properties':properties,'required':list(properties)})
    arguments={'type':'array','maxItems':4 if branches else 0,'items':{'anyOf':branches} if branches else {'type':'object'}}
    return {'type':'object','additionalProperties':False,'properties':{'arguments':arguments},'required':['arguments']}


def settings_for(units):
    from pipeline import settings
    out=settings()
    out['response_format']={'type':'json_schema','json_schema':{'name':'grounded_argument','strict':True,'schema':extraction_schema(units)}}
    return out


def validate(output,units):
    validate_extraction(output,units)
    byid={u['id']:u for u in units}
    for a in output['arguments']:require(byid[a['conclusion']]['source']!='title','title is context, not a comment-author conclusion anchor')
    return output
