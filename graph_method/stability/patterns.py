import collections
import hashlib
import itertools
import json
import random


FEATURES=['operator','stance','commitment','scope_change','alternatives','chain_bucket','escalation']


def features(argument):
    return {k:argument.get(k,'unannotated') for k in FEATURES if k!='chain_bucket'}|{'chain_bucket':'2+' if len(argument['chain'])>=2 else '0'}


def fits(constraints,argument):return all(features(argument)[k]==v for k,v in constraints.items())


def mine_patterns(rows,min_articles=5,min_purity=.45,max_per_label=6):
    candidates={}
    totals=collections.Counter(r['gold'] for r in rows)
    for row in rows:
        if row['status']!='accepted':continue
        for index,arg in enumerate(row['extraction']['arguments']):
            f=features(arg)
            if f['operator'] in ['other','evidence','analogy']:continue
            fields=[k for k in FEATURES if k!='operator' and f[k] not in ['na','unspecified','unclear','unannotated']]
            for count in range(min(2,len(fields))+1):
                for subset in itertools.combinations(fields,count):
                    constraints={k:f[k] for k in ['operator',*subset]};key=json.dumps(constraints,sort_keys=True)
                    candidates.setdefault(key,constraints)
    patterns=[]
    for key,constraints in candidates.items():
        matches=[r for r in rows if r['status']=='accepted' and any(fits(constraints,a) for a in r['extraction']['arguments'])]
        label_articles=collections.defaultdict(set)
        for r in matches:label_articles[r['gold']].add(r['article_id'])
        for label,articles in label_articles.items():
            if len(articles)<min_articles:continue
            outside={(r['gold'],r['article_id']) for r in matches if r['gold']!=label}
            purity=len(articles)/(len(articles)+len(outside))
            if purity<min_purity:continue
            own=[r for r in matches if r['gold']==label]
            coverage=len(own)/totals[label]
            quality=2*purity*coverage/(purity+coverage) if purity+coverage else 0
            witnesses=[]
            for row in own:
                index,arg=next((i,a) for i,a in enumerate(row['extraction']['arguments']) if fits(constraints,a))
                witnesses.append({'sample_id':row['sample_id'],'article_id':row['article_id'],'argument_index':index,'mapping':{'premise':'u'+str(arg['premises'][0]),'inference':'a'+str(index),'conclusion':'u'+str(arg['conclusion'])}})
            pid=hashlib.sha256((label+key).encode()).hexdigest()[:14]
            patterns.append({'id':pid,'label':label,'constraints':constraints,'graph':{'nodes':[{'id':'premise','kind':'proposition'},{'id':'inference','kind':'inference',**constraints},{'id':'conclusion','kind':'proposition'}],'edges':[{'src':'premise','rel':'PREMISE_OF','dst':'inference'},{'src':'inference','rel':'CONCLUDES','dst':'conclusion'}]},'positive_articles':len(articles),'outside_label_articles':len(outside),'purity':purity,'coverage':coverage,'quality':quality,'witnesses':witnesses})
    result=[]
    for label in sorted(totals):
        choices=sorted((p for p in patterns if p['label']==label),key=lambda p:(-p['quality'],-p['positive_articles'],len(p['constraints']),p['id']))
        # Keep the broad operator core and a small number of genuinely different refinements.
        chosen=[];signatures=set()
        for p in choices:
            signature=(p['constraints']['operator'],tuple(sorted(p['constraints'].items())))
            if signature in signatures:continue
            signatures.add(signature);chosen.append(p)
            if len(chosen)==max_per_label:break
        result.extend(chosen)
    return result


def retrieve(patterns,row,top_k=3):
    if row['status']!='accepted':return []
    ranked=[]
    for pattern in patterns:
        best=None
        for index,arg in enumerate(row['extraction']['arguments']):
            f=features(arg);weights={k:(4 if k=='operator' else 1) for k in pattern['constraints']}
            agreement=sum(weights[k] for k,v in pattern['constraints'].items() if f[k]==v)/sum(weights.values())
            operator_match=f['operator']==pattern['constraints']['operator']
            if not operator_match:continue
            score=agreement*pattern['quality']
            c={'id':'','label':pattern['label'],'pattern_id':pattern['id'],'constraints':pattern['constraints'],'argument_index':index,'mapping':{'premise':'u'+str(arg['premises'][0]),'inference':'a'+str(index),'conclusion':'u'+str(arg['conclusion'])},'premise_unit_ids':arg['premises'],'conclusion_unit_id':arg['conclusion'],'match_type':'exact' if agreement==1 else 'partial','structural_score':agreement,'pattern_purity':pattern['purity'],'pattern_article_support':pattern['positive_articles'],'retrieval_score':score}
            if best is None or c['retrieval_score']>best['retrieval_score']:best=c
        if best:ranked.append(best)
    ranked.sort(key=lambda c:(-c['retrieval_score'],-c['structural_score'],c['label'],c['pattern_id']))
    chosen=[];labels=set()
    for c in ranked:
        if c['label'] in labels:continue
        labels.add(c['label']);c['id']='c'+str(len(chosen));chosen.append(c)
        if len(chosen)==top_k:break
    return chosen


def bootstrap_recovery(patterns,rows,rounds=30,seed=20261017,min_articles=5,min_purity=.45):
    rng=random.Random(seed);articles=sorted({r['article_id'] for r in rows},key=str)
    result={p['id']:0 for p in patterns}
    for _ in range(rounds):
        sampled=set(rng.choices(articles,k=len(articles)))
        pool=[r for r in rows if r['article_id'] in sampled]
        for p in patterns:
            positive={r['article_id'] for r in pool if r['gold']==p['label'] and r['status']=='accepted' and any(fits(p['constraints'],a) for a in r['extraction']['arguments'])}
            negative={(r['gold'],r['article_id']) for r in pool if r['gold']!=p['label'] and r['status']=='accepted' and any(fits(p['constraints'],a) for a in r['extraction']['arguments'])}
            purity=len(positive)/(len(positive)+len(negative)) if positive or negative else 0
            result[p['id']]+=len(positive)>=min_articles and purity>=min_purity
    return {key:value/rounds for key,value in result.items()}
