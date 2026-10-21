"""Literal quote alignment; models never calculate source token offsets."""
import re
from copy import deepcopy
from ontology_v2 import P_ENUMS,KINDS,ROLES,validate_annotation,proposition_span,_object,_enum,_array,unit_tokens
from core import STANCES

def quote_source_payload(sample,units):
    return {'source':{k:sample.get(k,'') for k in ['comment','title','parent_comment']},'units':[{k:u[k] for k in ['id','source','text']} for u in units]}

def _anchor(ref,units):
    if set(ref)!={'unit','quote','occurrence'}:raise ValueError('exact quote anchor fields required')
    u=next((u for u in units if type(ref['unit']) is int and u['id']==ref['unit']),None)
    if u is None or not isinstance(ref['quote'],str) or not ref['quote'].strip() or type(ref['occurrence']) is not int or ref['occurrence']<0:raise ValueError('valid literal quote required')
    pattern=r'\s+'.join(re.escape(w) for w in ref['quote'].split())
    matches=list(re.finditer('(?=('+pattern+'))',u['text']))
    if ref['occurrence']>=len(matches):raise ValueError('Literal quote '+repr(ref['quote'])+' occurrence '+str(ref['occurrence'])+' not found in unit '+str(u['id'])+'. Copy its exact original spelling, including typos: '+repr(u['text'][:1000]))
    m=matches[ref['occurrence']];start,end=m.span(1)
    tokens=unit_tokens(u)
    indices=[i for i,t in enumerate(tokens) if t['start']-u['start']<end and t['end']-u['start']>start]
    if not indices:raise ValueError('empty quote')
    first,last=indices[0],indices[-1]+1
    omitted=u['text'][tokens[first]['start']-u['start']:start]+u['text'][end:tokens[last-1]['end']-u['start']]
    if any(c.isalnum() for c in omitted):raise ValueError('quote clips a word or negation')
    return dict(unit=u['id'],first=first,last=last)

def annotation_from_quotes(raw,units):
    if not isinstance(raw,dict) or set(raw)!={'propositions','applications'}:raise ValueError('exact graph fields required')
    ps,apps=raw['propositions'],raw['applications']
    if not isinstance(ps,list) or not isinstance(apps,list):raise ValueError('graph arrays required')
    def ids(items,prefix):
        out={}
        for i,x in enumerate(items):
            key=x.get('id') if isinstance(x,dict) else None
            if not isinstance(key,str) or not re.fullmatch(prefix+r'\d+',key) or key in out:raise ValueError('unique explicit IDs required')
            out[key]=i
        return out
    pids,aids=ids(ps,'p'),ids(apps,'a')
    def index(key,mapping):
        if key not in mapping:raise ValueError('unknown endpoint ID')
        return mapping[key]
    out={'propositions':[],'applications':[]}
    for p in ps:
        if set(p)!=set(P_ENUMS)|{'id','unit','quote','occurrence','implicit','gloss'}:raise ValueError('exact quoted proposition fields required')
        out['propositions'].append({**{k:v for k,v in p.items() if k not in ['id','unit','quote','occurrence']},**_anchor({k:p[k] for k in ['unit','quote','occurrence']},units)})
    for a in apps:
        if set(a)!={'id','kind','premises','target_kind','target','scheme','stance','scope_change','alternatives','evidence','roles'}:raise ValueError('exact quoted application fields required')
        if not isinstance(a['roles'],list) or any(not isinstance(r,dict) or set(r)!={'role','proposition'} for r in a['roles']):raise ValueError('exact role fields required')
        b=deepcopy(a);b.pop('id');b['premises']=[index(k,pids) for k in a['premises']]
        b['target']=index(a['target'],pids if a['target_kind']=='proposition' else aids)
        b['roles']=[{'role':r['role'],'proposition':index(r['proposition'],pids)} for r in a['roles']]
        b['evidence']=[_anchor(e,units) for e in a['evidence']];out['applications'].append(b)
    return validate_annotation(out,units)

def quote_graph_schema(units):
    anchor=dict(unit={'type':'integer','enum':[u['id'] for u in units]},quote={'type':'string'},occurrence={'type':'integer','minimum':0})
    pid=_enum(['p'+str(i) for i in range(48)]);aid=_enum(['a'+str(i) for i in range(16)])
    p=_object(dict(id=pid,**anchor,**{k:_enum(v) for k,v in P_ENUMS.items()},implicit={'type':'boolean'},gloss={'type':'string'}))
    a=_object(dict(id=aid,kind=_enum(KINDS),premises=_array(pid,48,1),target_kind=_enum(['proposition','application']),target=_enum(pid['enum']+aid['enum']),scheme=_enum(['other']),stance=_enum(STANCES),scope_change=_enum(['na']),alternatives=_enum(['na']),evidence=_array(_object(anchor),None,1),roles=_array(_object(dict(role=_enum(ROLES),proposition=pid)))))
    return _object(dict(propositions=_array(p,48),applications=_array(a,16)))

def annotation_to_quotes(annotation,units):
    def anchor(p):
        span=proposition_span(p,units);u=next(u for u in units if u['id']==p['unit'])
        return dict(unit=p['unit'],quote=span['text'],occurrence=sum(1 for m in re.finditer(re.escape(span['text']),u['text']) if m.start()<span['start']-u['start']))
    out=deepcopy(annotation)
    out['propositions']=[{**{k:v for k,v in p.items() if k not in ['unit','first','last']},'id':'p'+str(i),**anchor(p)} for i,p in enumerate(annotation['propositions'])]
    for i,a in enumerate(out['applications']):
        a['id']='a'+str(i);a['premises']=['p'+str(j) for j in a['premises']];a['target']=('p' if a['target_kind']=='proposition' else 'a')+str(a['target'])
        a['roles']=[dict(role=r['role'],proposition='p'+str(r['proposition'])) for r in a['roles']];a['evidence']=[anchor(e) for e in a['evidence']]
    return out

def readable_propositions(annotation,units):
    return [dict(id='p'+str(i),index=i,**p,text=proposition_span(p,units)['text']) for i,p in enumerate(annotation['propositions'])]
