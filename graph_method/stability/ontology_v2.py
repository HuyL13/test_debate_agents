"""Grounded source ontology. Validation enforces structure, never truth or logic."""
import re
from core import OPERATORS, STANCES, SCOPES, ALTERNATIVES
from unitization import split_units_v5

P_ENUMS=dict(owner=['current_author','parent_author','attributed','context','unclear'],speech_act=['assert','recommend','question','report','hypothetical','meta'],modality=['certain','probable','possible','unspecified'],polarity=['positive','negative','unclear'],event_role=['none','condition','outcome','action'])
KINDS=['support','rebut','undercut','preference','projection','qualification','adoption','concession']
ROLES=['source','sample','population','initial','consequence','preferred','deprioritized','choice','natural_property','tradition','claim','rejected_warrant','criterion','collective','source_case','target_case','adoption_cue']

def source_units(sample):
    units=split_units_v5(sample)
    for u in units:
        u['tokens']=[dict(index=i,text=m.group(),start=u['start']+m.start(),end=u['start']+m.end()) for i,m in enumerate(re.finditer(r'\S+',u['text']))]
        u['numbered_tokens']=' '.join(str(t['index'])+':'+t['text'] for t in u['tokens'])
    return units

def source_payload(sample,units):
    return {'source':{k:sample.get(k,'') for k in ['comment','title','parent_comment']},'units':units}

def _require(ok,message):
    if not ok:raise ValueError(message)

def proposition_span(p,units):
    _require(isinstance(p,dict),'span object required')
    byid={u['id']:u for u in units}
    _require(type(p.get('unit')) is int and p['unit'] in byid,'real unit required')
    u=byid[p['unit']];ts=list(re.finditer(r'\S+',u['text']))
    first,last=p.get('first'),p.get('last')
    _require(type(first) is int and type(last) is int and 0<=first<last<=len(ts),'invalid token bounds')
    a,b=ts[first].start(),ts[last-1].end()
    return dict(source=u['source'],start=u['start']+a,end=u['start']+b,text=u['text'][a:b])

def has_positive_endorsement(text):
    # A conservative explicit-cue license, not proof of the contextual target.
    pattern=r"\b(?:(?:i|we)\s+(?:(?:fully|totally|completely)\s+)?agree|(?:i|we)\s+could(?:n't| not)\s+agree\s+more|that(?:'s| is)\s+(?:true|right|correct)|you(?:'re| are)\s+(?:right|correct))\b|^\s*(?:yes\b|(?:indeed|correct)(?=\s*[,.:;!?]|\s*$))"
    for match in re.finditer(pattern,text,re.I):
        prefix=re.split(r"[,;.!?]|\bbut\b|\bhowever\b",text[:match.start()],flags=re.I)[-1]
        last_words=' '.join(prefix.split()[-5:])
        if not re.search(r"\b(?:not|never|hardly|cannot|nobody)\b|n't\b",last_words,re.I):return True
    return False


def adoption_cue_indices(ps,units):
    return [i for i,p in enumerate(ps) if not p['implicit'] and p['owner']=='current_author' and p['speech_act'] in ['assert','recommend','meta'] and (lambda s:s['source']=='comment' and has_positive_endorsement(s['text']))(proposition_span(p,units))]


def _object(properties):return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
def _enum(values):return dict(type='string',enum=list(values))
def _array(items,maximum=None,minimum=0):
    out=dict(type='array',items=items,minItems=minimum)
    if maximum is not None:out['maxItems']=maximum
    return out

def annotation_schema(units):
    # Unit-specific oneOf branches constrain token ceilings in structured output.
    anchors=[]
    for u in units:
        count=len(re.findall(r'\S+',u['text']))
        anchors.append(dict(unit=dict(type='integer',enum=[u['id']]),first=dict(type='integer',minimum=0,maximum=count-1),last=dict(type='integer',minimum=1,maximum=count)))
    common={**{k:_enum(v) for k,v in P_ENUMS.items()},'implicit':dict(type='boolean'),'gloss':dict(type='string')}
    p={'anyOf':[_object({**a,**common}) for a in anchors]} if anchors else {'not':{}}
    ev={'anyOf':[_object(a) for a in anchors]} if anchors else {'not':{}}
    idx=dict(type='integer',minimum=0,maximum=47)
    app=_object(dict(kind=_enum(KINDS),premises=_array(idx,48,1),target_kind=_enum(['proposition','application']),target=dict(type='integer',minimum=0,maximum=47),scheme=_enum(OPERATORS),stance=_enum(STANCES),scope_change=_enum(SCOPES),alternatives=_enum(ALTERNATIVES),evidence=_array(ev,None,1),roles=_array(_object(dict(role=_enum(ROLES),proposition=idx)))))
    return _object(dict(propositions=_array(p,48),applications=_array(app,16)))

def validate_annotation(annotation,units):
    _require(isinstance(annotation,dict) and set(annotation)=={'propositions','applications'},'exact annotation keys required')
    ps,apps=annotation['propositions'],annotation['applications']
    _require(isinstance(ps,list) and len(ps)<=48,'at most 48 propositions')
    _require(isinstance(apps,list) and len(apps)<=16,'at most 16 applications')
    for p in ps:
        _require(isinstance(p,dict) and set(p)==set(P_ENUMS)|{'unit','first','last','implicit','gloss'},'exact proposition fields required')
        span=proposition_span(p,units)
        for k,values in P_ENUMS.items():_require(p[k] in values,'invalid '+k)
        _require(type(p['implicit']) is bool and isinstance(p['gloss'],str),'implicit boolean and gloss string required')
        _require(not p['implicit'] or bool(p['gloss'].strip()),'implicit proposition requires gloss')
        _require(p['speech_act']!='meta' or p['event_role']=='none','meta proposition cannot be event')
        _require(p['speech_act']!='recommend' or p['event_role']!='outcome','recommendation cannot be projected outcome')
        _require(span['source']=='comment' or p['owner']!='current_author','context source cannot silently belong to current author')
    def index(i,n):return type(i) is int and 0<=i<n
    for a in apps:
        _require(isinstance(a,dict) and set(a)=={'kind','premises','target_kind','target','scheme','stance','scope_change','alternatives','evidence','roles'},'exact application fields required')
        for k,values in [('kind',KINDS),('target_kind',['proposition','application']),('scheme',OPERATORS),('stance',STANCES),('scope_change',SCOPES),('alternatives',ALTERNATIVES)]:_require(a[k] in values,'invalid '+k)
        _require(isinstance(a['premises'],list) and bool(a['premises']) and all(index(i,len(ps)) for i in a['premises']),'real premises required')
        _require(len(set(a['premises']))==len(a['premises']),'distinct premises required')
        _require(index(a['target'],len(ps) if a['target_kind']=='proposition' else len(apps)),'real target required')
        _require(a['target_kind']!='proposition' or a['target'] not in a['premises'],'no proposition self-target')
        _require(isinstance(a['evidence'],list) and bool(a['evidence']),'nonempty evidence required')
        for e in a['evidence']:
            _require(isinstance(e,dict) and set(e)=={'unit','first','last'},'exact evidence fields required');proposition_span(e,units)
        _require(isinstance(a['roles'],list),'roles array required')
        for r in a['roles']:_require(isinstance(r,dict) and set(r)=={'role','proposition'} and r['role'] in ROLES and index(r['proposition'],len(ps)),'real role binding required')
        if a['kind'] in ['concession','adoption']:_require(a['scheme']=='other' and a['scope_change']=='na' and a['alternatives']=='na','discourse/adoption reference is not an argumentative warrant')
        if a['kind']=='undercut':_require(a['target_kind']=='application','undercut must target application')
        if a['kind']=='rebut':_require(a['target_kind']=='proposition','rebut must target proposition')
        if a['kind']=='projection':
            _require(a['target_kind']=='proposition','projection must target event proposition')
            for i in a['premises']+[a['target']]:_require(ps[i]['event_role']!='none' and ps[i]['speech_act']!='meta','projection endpoints must be event mentions')
            _require(ps[a['target']]['event_role']=='outcome','projection target must be outcome')
        if a['kind']=='preference':
            preferred={r['proposition'] for r in a['roles'] if r['role']=='preferred'};deprioritized={r['proposition'] for r in a['roles'] if r['role']=='deprioritized'}
            _require(bool(preferred) and bool(deprioritized) and not preferred&deprioritized,'preference needs distinct preferred/deprioritized roles')
        if a['kind']=='adoption':
            _require(a['target_kind']=='proposition' and proposition_span(ps[a['target']],units)['source']!='comment' and a['stance']=='uses','adoption needs contextual target and uses stance')
            _require(any(proposition_span(e,units)['source']=='comment' for e in a['evidence']),'adoption needs reply evidence')
            cues={r['proposition'] for r in a['roles'] if r['role']=='adoption_cue'}
            eligible=set(adoption_cue_indices(ps,units))
            _require(bool(cues) and cues<=set(a['premises']) and cues<=eligible,'adoption requires an explicit positive endorsement cue in an actual current-author premise; do not fabricate adoption to import context')
            _require(not ps[a['target']]['implicit'],'explicit adoption needs a literal contextual claim, not an invented hypothesis')
            _require(any((lambda s:s['source']=='comment' and has_positive_endorsement(s['text']))(proposition_span(e,units)) for e in a['evidence']),'adoption evidence must quote the positive endorsement itself')
    adopted={a['target'] for a in apps if a['kind']=='adoption'}
    for a in apps:
        if a['stance']=='uses' and a['kind']!='adoption':
            for i in a['premises']:
                _require(proposition_span(ps[i],units)['source']=='comment' or i in adopted,'contextual premise needs explicit adoption before author use')
    visiting,done=set(),set()
    def visit(i):
        _require(i not in visiting,'cyclic application dependency')
        if i in done:return
        visiting.add(i)
        if apps[i]['target_kind']=='application':visit(apps[i]['target'])
        visiting.remove(i);done.add(i)
    for i in range(len(apps)):visit(i)
    return annotation

def compile_graph(annotation,units):
    validate_annotation(annotation,units);nodes=[];edges=[];spans={}
    def node(id,type,**kw):nodes.append(dict(id=id,type=type,**kw));return id
    def edge(source,type,target,**kw):edges.append(dict(source=source,type=type,target=target,**kw))
    def anchor(obj,p):
        span=proposition_span(p,units);key=(span['source'],span['start'],span['end'])
        if key not in spans:spans[key]=node('span'+str(len(spans)),'SourceSpan',**span)
        edge(obj,'ANCHORS',spans[key]);return spans[key]
    ps=annotation['propositions']
    for i,p in enumerate(ps):
        pid='p'+str(i);sid='assertion'+str(i);span=proposition_span(p,units)
        node(pid,'Proposition',index=i,content=p['gloss'] if p['implicit'] else span['text'],hypothesized=p['implicit'],**p);anchor(pid,p)
        node(sid,'Assertion',proposition=pid,owner=p['owner'],speech_act=p['speech_act'],modality=p['modality'],polarity=p['polarity'],hypothesized=p['implicit'],status='hypothesized' if p['implicit'] else 'explicit');anchor(sid,p)
        relation={'assert':'ASSERTS','report':'REPORTS','recommend':'RECOMMENDS','question':'QUERIES','hypothetical':'HYPOTHESIZES','meta':'DISCUSSES'}[p['speech_act']]
        edge(sid,'HYPOTHESIZES' if p['implicit'] else relation,pid)
        if p['event_role']!='none' and p['speech_act']!='meta':
            eid=node('event'+str(i),'EventMention',proposition=pid,event_role=p['event_role'],modality=p['modality'],hypothesized=p['implicit']);anchor(eid,p);edge(eid,'CONTENT',pid)
    for i,a in enumerate(annotation['applications']):
        aid='a'+str(i);typ='ReferenceApplication' if a['kind']=='adoption' else 'DiscourseApplication' if a['kind']=='concession' else 'ConflictApplication' if a['kind'] in ['rebut','undercut'] else 'PreferenceApplication' if a['kind']=='preference' else 'InferenceApplication'
        node(aid,typ,index=i,**a)
        for e in a['evidence']:anchor(aid,e)
        for p in a['premises']:edge('p'+str(p),'ADOPTION_CUE' if a['kind']=='adoption' else 'CONCEDED_CONTENT' if a['kind']=='concession' else 'PREMISE_OF',aid,assertion='assertion'+str(p))
        target=('p' if a['target_kind']=='proposition' else 'a')+str(a['target']);edge(aid,'TARGETS',target)
        if a['kind'] in ['rebut','undercut','adoption']:edge(aid,{'rebut':'REBUTS','undercut':'UNDERCUTS','adoption':'ADOPTS'}[a['kind']],target)
        if a['kind']=='projection':
            for p in a['premises']:edge('event'+str(p),'PROJECTED_NEXT','event'+str(a['target']),application=aid)
        if a['kind']=='preference':
            for x in a['roles']:
                if x['role']=='preferred':
                    for y in a['roles']:
                        if y['role']=='deprioritized':edge('p'+str(x['proposition']),'PREFERS_OVER','p'+str(y['proposition']),application=aid)
        for r in a['roles']:edge(aid,'ROLE','p'+str(r['proposition']),role=r['role'])
        hid=node('scheme'+str(i),'SchemeHypothesis',scheme=a['scheme'],status='not_applicable' if a['kind'] in ['concession','adoption'] else 'ambiguous' if a['scheme']=='other' else 'unverified',roles=a['roles'],stance=a['stance']);edge(hid,'CLASSIFIES',aid)
        for e in a['evidence']:anchor(hid,e)
    return dict(nodes=nodes,edges=edges)
