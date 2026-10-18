"""Scheme-specific named role slots constrained to each directed application."""
from copy import deepcopy
from ontology_v2 import _object,_enum,_array,proposition_span
from warrants_v2 import REQUIRED_ROLES,validate_typing,typing_schema,PROMPT
from core import OPERATORS,SCOPES,ALTERNATIVES,invoke
from pipeline import MODEL,settings
from source_quotes_v2 import quote_source_payload,readable_propositions


def canonicalize_slots(raw,annotation,units):
    if not isinstance(raw,dict) or set(raw)!={'annotations'} or not isinstance(raw['annotations'],dict):raise ValueError('exact annotations required')
    out={'annotations':{}}
    for key,t in raw['annotations'].items():
        if not isinstance(t,dict) or set(t)!={'warrant','evidence','reason'}:raise ValueError('exact warrant slot fields required')
        w=t['warrant']
        if not isinstance(w,dict) or set(w)!={'scheme','scope_change','alternatives','roles'}:raise ValueError('exact scheme and named role slots required')
        scheme=w['scheme']
        if scheme not in REQUIRED_ROLES or not isinstance(w['roles'],dict) or set(w['roles'])!=REQUIRED_ROLES[scheme]:raise ValueError('scheme requires its exact named role slots')
        roles=[]
        for role,values in w['roles'].items():
            if not isinstance(values,list) or not values:raise ValueError('nonempty grounded role bindings required')
            roles.extend(dict(role=role,proposition=j) for j in values)
        out['annotations'][key]=dict(scheme=scheme,scope_change=w['scope_change'],alternatives=w['alternatives'],roles=roles,evidence=deepcopy(t['evidence']),reason=t['reason'])
    return validate_typing(out,annotation,units)


def _within(ps,units,j,endpoints):
    if j in endpoints:return True
    if ps[j]['implicit']:return False
    s=proposition_span(ps[j],units)
    for k in endpoints:
        if ps[k]['implicit']:continue
        t=proposition_span(ps[k],units)
        if s['source']==t['source'] and t['start']<=s['start'] and s['end']<=t['end']:return True
    return False


def slot_schema(annotation,units):
    old=typing_schema(annotation,units)['properties']['annotations']['properties'];ps=annotation['propositions'];items={}
    for i,a in enumerate(annotation['applications']):
        branches=[]
        for scheme in OPERATORS:
            if a['kind'] in ['concession','adoption'] and scheme!='other':continue
            if scheme=='priority_comparison' and a['kind']!='preference':continue
            if scheme=='causal_projection' and not any(x['kind']=='projection' for x in annotation['applications']):continue
            roles={};valid=True
            for role in sorted(REQUIRED_ROLES[scheme]):
                endpoints=None
                if role in ['source','collective','tradition','natural_property','sample','source_case','criterion']:endpoints=a['premises']
                if role=='initial' and a['kind']=='projection':endpoints=a['premises']
                if role in ['claim','population','target_case'] or role=='consequence' and a['kind']=='projection':
                    if a['target_kind']=='proposition':endpoints=[a['target']]
                allowed=[j for j in range(len(ps)) if endpoints is None or _within(ps,units,j,endpoints)]
                if role=='claim' and a['target_kind']=='proposition':allowed=[a['target']]
                if scheme=='causal_projection':
                    projection_endpoints=[j for x in annotation['applications'] if x['kind']=='projection' for j in (x['premises'] if role=='initial' else [x['target']])]
                    allowed=[j for j in allowed if _within(ps,units,j,projection_endpoints)]
                if role=='source':allowed=[j for j in allowed if ps[j]['owner']=='attributed' or ps[j]['speech_act']=='report']
                if not allowed:valid=False;break
                roles[role]=_array({'type':'integer','enum':allowed},len(allowed),1)
            if not valid:continue
            branches.append(_object(dict(scheme=_enum([scheme]),scope_change=_enum(SCOPES if scheme=='generalization' else ['na']),alternatives=_enum(ALTERNATIVES if scheme=='alternatives' else ['na']),roles=_object(roles))))
        common=old['a'+str(i)]['properties']
        items['a'+str(i)]=_object(dict(warrant={'anyOf':branches},evidence=deepcopy(common['evidence']),reason=deepcopy(common['reason'])))
    return _object(dict(annotations=_object(items)))


def type_warrant_slots(sample,units,annotation,repeat=0,thinking=True,invoke_fn=invoke):
    if not annotation['applications']:return dict(status='not_applicable',call_id=None,output={'annotations':{}})
    fixed={}
    for i,a in enumerate(annotation['applications']):
        if a['kind'] in ['concession','adoption']:
            fixed['a'+str(i)]=dict(warrant=dict(scheme='other',scope_change='na',alternatives='na',roles={}),evidence=deepcopy(a['evidence']),reason='Code-owned non-argumentative '+a['kind']+' application; no argumentative warrant assigned.')
    def compile_output(raw):
        if not isinstance(raw,dict) or set(raw)!={'annotations'} or not isinstance(raw['annotations'],dict):raise ValueError('exact annotations object required')
        expected={'a'+str(i) for i in range(len(annotation['applications']))}-set(fixed)
        if set(raw['annotations'])!=expected:raise ValueError('only requested argumentative application IDs may be typed')
        return canonicalize_slots({'annotations':{**fixed,**raw['annotations']}},annotation,units)
    if len(fixed)==len(annotation['applications']):return dict(status='not_applicable',call_id=None,output=compile_output({'annotations':{}}))
    schema=slot_schema(annotation,units)
    props=schema['properties']['annotations']['properties']
    for key in fixed:props.pop(key)
    schema['properties']['annotations']['required']=list(props)
    config=settings();config.update(max_tokens=6144,chat_template_kwargs={'enable_thinking':thinking,**({'reasoning_budget':1024} if thinking else {})})
    config['response_format']={'type':'json_schema','json_schema':{'name':'named_warrant_slots','strict':True,'schema':schema}}
    relations=[{'id':'a'+str(i),**{k:a[k] for k in ['kind','premises','target_kind','target','stance','roles']}} for i,a in enumerate(annotation['applications']) if 'a'+str(i) not in fixed]
    payload={**quote_source_payload(sample,units),'propositions':readable_propositions(annotation,units),'applications':relations}
    prompt=PROMPT+'\nOUTPUT FORMAT OVERRIDE: for each a-ID return {warrant:{scheme,scope_change,alternatives,roles:{required_role:[proposition indices]}},evidence,reason}. The schema provides the exact required named role slots for each available scheme. Fill every required slot with real grounded propositions. There is no role-name array. Select evidence or other with empty role object if a specific warrant cannot be grounded; never invent a source or change application endpoints.'
    rec=invoke_fn(MODEL,'warrant_slots_v2',sample['sample_id'],prompt,payload,compile_output,'ontology-v2-warrant-slots-r4'+('' if thinking else '-no-thinking'),repeat,config)
    return {**rec,'output':compile_output(rec['output'])} if rec['status']=='accepted' else rec
