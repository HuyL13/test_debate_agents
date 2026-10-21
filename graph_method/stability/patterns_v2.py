"""Native directed V2 motifs. No fallacy labels enter source annotation."""
import collections
import hashlib
import json
import random

MATCHING_POLICY='directed-role-core-soft-facets-r1'
SOFT_FIELDS=['modality','polarity','speech_act','event_role']

def attribute_profile(row,mapping):
    return {canonical:{k:row['annotation']['propositions'][int(actual[1:])][k] for k in SOFT_FIELDS}
            for canonical,actual in mapping.items() if canonical.startswith('p')}

def soft_similarity(profile,reference):
    comparisons=[profile[p][k]==reference[p][k] for p in profile if p in reference for k in SOFT_FIELDS]
    return sum(comparisons)/len(comparisons) if comparisons else 0.0


def _key(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))


def witnessed_subgraph(row,mapping):
    """Export compiler nodes, including exact spans, scoped to this mapping."""
    ids=set(mapping.values())
    graph=row.get('graph',{'nodes':[],'edges':[]})
    adopted={edge['source'] for edge in graph['edges'] if edge.get('type')=='ADOPTS' and edge.get('target') in ids}
    ids.update(adopted)
    for edge in graph['edges']:
        if edge.get('target') in adopted and edge.get('type') in ['PREMISE_OF','ADOPTION_CUE']:ids.add(edge['source'])
        if edge.get('source') in adopted and edge.get('type')=='ROLE':ids.add(edge['target'])
    for actual in list(ids):
        if actual.startswith('p') and actual[1:].isdigit():
            ids.update(['assertion'+actual[1:],'event'+actual[1:]])
        if actual.startswith('a') and actual[1:].isdigit():ids.add('scheme'+actual[1:])
    graph=row.get('graph',{'nodes':[],'edges':[]})
    for edge in graph['edges']:
        if edge.get('type')=='ANCHORS' and edge.get('source') in ids:ids.add(edge['target'])
    nodes=[n for n in graph['nodes'] if n['id'] in ids];present={n['id'] for n in nodes}
    return {'nodes':nodes,'edges':[e for e in graph['edges'] if e.get('source') in present and e.get('target') in present]}


def application_subgraph(row,index,resolution="core"):
    """Canonical root motif with all premises/roles and recursive targets.

    Application targets form a rooted chain under the V2 contract. Proposition
    colors include semantic attributes and every incidence in that chain. Equal
    colors are interchangeable vertices, so source IDs and array order cannot
    change the resulting graph. Adjacent optional applications are not required.
    """
    annotation=row['annotation'];apps=annotation['applications'];props=annotation['propositions']
    ordered=[];current=index
    while current not in ordered:
        ordered.append(current);app=apps[current]
        if app['target_kind']!='application':break
        current=app['target']
    amap={i:'a'+str(n) for n,i in enumerate(ordered)}
    participants=set();incidence=collections.defaultdict(list)
    for i in ordered:
        a=apps[i];aid=amap[i]
        for p in a['premises']:
            participants.add(p);incidence[p].append((aid,'PREMISE_OF'))
        if a['target_kind']=='proposition':
            p=a['target'];participants.add(p);incidence[p].append((aid,'TARGETS'))
        for r in a['roles']:
            p=r['proposition'];participants.add(p);incidence[p].append((aid,'ROLE:'+r['role']))
    # These facets remain on source graphs and witness profiles. They may
    # influence candidate ranking, but do not split structural motif identity.
    if resolution not in ['core','strict']:raise ValueError('unknown matching resolution')
    fields=['owner','implicit']+(SOFT_FIELDS if resolution=='strict' else [])
    attributes={p:{k:props[p][k] for k in fields} for p in participants}
    def color(p):return _key([attributes[p],sorted(incidence[p])])
    pmap={p:'p'+str(n) for n,p in enumerate(sorted(participants,key=color))}
    nodes=[{'id':pmap[p],'kind':'Proposition',**attributes[p]} for p in participants];edges=[]
    for i in ordered:
        a=apps[i];aid=amap[i]
        nodes.append({'id':aid,'kind':a['kind'],**{k:a[k] for k in ['scheme','stance','scope_change','alternatives']}})
        for p in a['premises']:edges.append({'src':pmap[p],'rel':'PREMISE_OF','dst':aid})
        target=pmap[a['target']] if a['target_kind']=='proposition' else amap[a['target']]
        edges.append({'src':aid,'rel':'TARGETS','dst':target})
        for r in a['roles']:edges.append({'src':pmap[r['proposition']],'rel':'ROLE:'+r['role'],'dst':aid})
    mapping={v:'p'+str(k) for k,v in pmap.items()}
    mapping.update({v:'a'+str(k) for k,v in amap.items()})
    graph={'root':'a0','nodes':sorted(nodes,key=lambda n:n['id']),'edges':sorted(edges,key=_key)}
    return graph,mapping



def _occurrences(rows,resolution="core"):
    from semantic_review_v2 import eligible_application
    for row in rows:
        if row.get('status')!='accepted':continue
        for i,a in enumerate(row['annotation']['applications']):
            if a['kind'] in ['concession','adoption']:continue
            if not eligible_application(row,i):continue
            graph,mapping=application_subgraph(row,i,resolution)
            yield _key(graph),row,i,a,graph,mapping


def mine_patterns(rows,min_articles=5,min_purity=.45,max_per_label=6,resolution="core"):
    groups=collections.defaultdict(list)
    for item in _occurrences(rows,resolution):groups[item[0]].append(item)
    totals=collections.defaultdict(set)
    for r in rows:totals[r['gold']].add(r['article_id'])
    patterns=[]
    for signature,items in groups.items():
        for label in sorted({x[1]['gold'] for x in items}):
            own=[x for x in items if x[1]['gold']==label];positive={x[1]['article_id'] for x in own}
            outside={(x[1]['gold'],x[1]['article_id']) for x in items if x[1]['gold']!=label}
            purity=len(positive)/(len(positive)+len(outside))
            if len(positive)<min_articles or purity<min_purity:continue
            coverage=len(positive)/len(totals[label]);quality=2*purity*coverage/(purity+coverage)
            witnesses=[]
            for _,r,i,a,g,m in own:
                witnesses.append({'sample_id':r['sample_id'],'article_id':r['article_id'],'application_index':i,'mapping':m,'application':a,'source_graph':witnessed_subgraph(r,m),'attribute_profile':attribute_profile(r,m)})
            # Each alternative is independent: no union can introduce cross paths.
            prototype={'id':'prototype0','graph':own[0][4],'witnesses':witnesses}
            patterns.append({'id':hashlib.sha256((str(label)+signature).encode()).hexdigest()[:16],'label':label,'constraints':{k:own[0][3][k] for k in ['kind','scheme','stance','scope_change','alternatives']},'signature':signature,'graph':own[0][4],'prototypes':[prototype],'merged_graph':{'composition':'alternative_prototypes','prototypes':[prototype]},'positive_articles':len(positive),'outside_label_articles':len(outside),'purity':purity,'coverage':coverage,'quality':quality,'witnesses':witnesses})
            patterns[-1]['matching_policy']=MATCHING_POLICY if resolution=='core' else 'directed-role-strict-facets-r1'
            patterns[-1]['resolution']=resolution
    result=[]
    for label in sorted(totals):result.extend(sorted((p for p in patterns if p['label']==label),key=lambda p:(-p['quality'],-p['positive_articles'],p['id']))[:max_per_label])
    return result


def retrieve(patterns,row,top_k=3,min_bootstrap=.8,max_per_label=3):
    """Keep top labels and bounded distinct source mappings for final verification."""
    if row.get('status')!='accepted' or top_k<=0 or max_per_label<=0:return []
    matches=[]
    resolutions=sorted({p.get('resolution','core') for p in patterns})
    occurrences=[(resolution,item) for resolution in resolutions for item in _occurrences([row],resolution)]
    for resolution,(signature,_,i,a,g,m) in occurrences:
        for p in patterns:
            if p.get('resolution','core')!=resolution:continue
            if p.get('bootstrap_recovery',0)<min_bootstrap or signature!=p['signature']:continue
            matches.append({'label':p['label'],'pattern_id':p['id'],'prototype_id':'prototype0','application_index':i,'kind':a['kind'],'scheme':a['scheme'],'scheme_status':'uncertain' if a['scheme']=='other' else 'hypothesis','stance':a['stance'],'premise_proposition_ids':a['premises'],'target_kind':a['target_kind'],'target_id':a['target'],'roles':a['roles'],'mapping':m,'subgraph':g,'source_graph':witnessed_subgraph(row,m),'match_type':'exact','structural_score':1.0,'pattern_purity':p['purity'],'pattern_article_support':p['positive_articles'],'retrieval_score':p['quality']})
            profile=attribute_profile(row,m)
            score=max((soft_similarity(profile,w.get('attribute_profile',{})) for w in p['witnesses']),default=0.0)
            matches[-1].update(match_type='exact_directed_role_core',matching_policy=p.get('matching_policy',MATCHING_POLICY),resolution=resolution,source_attribute_profile=profile,soft_attribute_score=score,retrieval_score=p['quality']*(.9+.1*score))
    matches.sort(key=lambda c:(-c['retrieval_score'],c['label'],c['pattern_id'],c['application_index']))
    labels=[]
    for c in matches:
        if c['label'] not in labels:labels.append(c['label'])
        if len(labels)>=top_k:break
    chosen=[];seen=set();counts=collections.Counter()
    for c in matches:
        label=c['label']
        if label not in labels or counts[label]>=max_per_label:continue
        # The same source application matching both resolutions is one
        # candidate, not two independent pieces of evidence.
        binding=(label,c['application_index'],tuple(sorted(c['premise_proposition_ids'])),c['target_kind'],c['target_id'])
        if binding in seen:continue
        seen.add(binding);counts[label]+=1;chosen.append(dict(c,id='c'+str(len(chosen))))
    return chosen


def bootstrap_recovery(patterns,rows,rounds=30,seed=20261017,min_articles=5,min_purity=.45):
    if rounds<=0:raise ValueError('rounds must be positive')
    articles=sorted({r['article_id'] for r in rows},key=str);rng=random.Random(seed);counts=collections.Counter()
    occurrences={resolution:list(_occurrences(rows,resolution)) for resolution in {p.get('resolution','core') for p in patterns}}
    for _ in range(rounds):
        sampled=set(rng.choices(articles,k=len(articles))) if articles else set()
        for p in patterns:
            matching=[r for sig,r,*_ in occurrences[p.get('resolution','core')] if sig==p['signature'] and r['article_id'] in sampled]
            positive={r['article_id'] for r in matching if r['gold']==p['label']};outside={(r['gold'],r['article_id']) for r in matching if r['gold']!=p['label']}
            if len(positive)>=min_articles and len(positive)/(len(positive)+len(outside))>=min_purity:counts[p['id']]+=1
    return {p['id']:counts[p['id']]/rounds for p in patterns}
