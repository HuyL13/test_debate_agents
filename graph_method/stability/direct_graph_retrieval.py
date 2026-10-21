"""Nearest TRAIN graphs without merged patterns or support thresholds."""
from collections import Counter
import math
from patterns_v2 import application_subgraph,_key

def features(row):
    features=Counter();mechanisms=set();cores=set()
    if row.get('status')!='accepted':return features,mechanisms,cores
    annotation=row['annotation'];props=annotation['propositions'];apps=annotation['applications']
    for i,a in enumerate(apps):
        if a['kind'] in ['adoption','concession']:continue
        graph,_=application_subgraph(row,i)
        cores.add(_key(graph));mechanisms.add((a['kind'],a['scheme'],a['stance'],a['alternatives'],a['scope_change']))
        root=(a['kind'],a['scheme'],a['stance'])
        features[('scheme',a['scheme'])]+=3
        features[('root',*root)]+=3
        features[('choices',a['scheme'],a['alternatives'])]+=2
        features[('scope',a['scheme'],a['scope_change'])]+=2
        features[('arity',*root,min(4,len(a['premises'])))]+=1
        for p in a['premises']:
            features[('directed_premise',*root,props[p]['owner'],props[p]['implicit'])]+=1
        if a['target_kind']=='proposition':
            p=a['target'];features[('directed_target',*root,props[p]['owner'],props[p]['implicit'])]+=1
        else:features[('target_application',*root,apps[a['target']]['kind'])]+=2
        for role in a['roles']:
            p=role['proposition'];endpoint='premise' if p in a['premises'] else 'target' if a['target_kind']=='proposition' and p==a['target'] else 'other'
            features[('role',*root,role['role'],endpoint)]+=3
        for p in set(a['premises'])|({a['target']} if a['target_kind']=='proposition' else set()):
            for field in ['modality','polarity','speech_act','event_role']:
                features[('facet',a['scheme'],field,props[p][field])]+=.15
        if a['target_kind']=='proposition':
            for b in apps:
                if a['target'] in b['premises']:features[('path',a['kind'],a['scheme'],b['kind'],b['scheme'])]+=2
    return features,mechanisms,cores

class GraphIndex:
    def __init__(self,rows):
        self.rows={r['sample_id']:r for r in rows if r.get('status')=='accepted' and r.get('split')=='induction'}
        self.data={sid:features(r) for sid,r in self.rows.items()}
        df=Counter(k for f,_,_ in self.data.values() for k in f)
        self.idf={k:1+math.log((len(self.rows)+1)/(n+1)) for k,n in df.items()}
        self.vectors={sid:self.vector(data[0]) for sid,data in self.data.items()}
    def vector(self,f):
        v={k:(1+math.log(1+x))*self.idf.get(k,1) for k,x in f.items()}
        norm=math.sqrt(sum(x*x for x in v.values())) or 1
        return {k:x/norm for k,x in v.items()}
    def search(self,query,mode='hybrid',top_k=8,max_per_label=2):
        if mode not in ['core','weighted','hybrid']:raise ValueError('Unknown mode')
        f,mechanisms,cores=features(query);v=self.vector(f);ranked=[]
        for sid,(tf,tm,tc) in self.data.items():
            row=self.rows[sid]
            if sid==query['sample_id'] or row['article_id']==query['article_id']:continue
            cosine=sum(x*self.vectors[sid].get(k,0) for k,x in v.items())
            core=len(cores&tc)/len(cores|tc) if cores|tc else 0
            mechanism=2*len(mechanisms&tm)/(len(mechanisms)+len(tm)) if mechanisms or tm else 0
            score=core if mode=='core' else cosine if mode=='weighted' else .65*cosine+.25*mechanism+.10*core
            if score>0:ranked.append(dict(sample_id=sid,label=row['gold'],article_id=row['article_id'],score=score,graph_cosine=cosine,mechanism_overlap=mechanism,core_overlap=core))
        ranked.sort(key=lambda r:(-r['score'],r['sample_id']))
        selected=[];counts=Counter();articles=set()
        for r in ranked:
            if counts[r['label']]>=max_per_label or r['article_id'] in articles:continue
            selected.append(r);counts[r['label']]+=1;articles.add(r['article_id'])
            if len(selected)>=top_k:break
        return selected
