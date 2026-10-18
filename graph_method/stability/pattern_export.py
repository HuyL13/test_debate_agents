"""One provenance-preserving graph per label; alternative cores stay separate."""
from copy import deepcopy


def merge_pattern_graphs(patterns, labels=None):
    result={}
    for label in sorted(set(labels or [])|{p['label'] for p in patterns}):
        selected=[p for p in patterns if p['label']==label]
        graph={'label':label,'status':'supported' if selected else 'no_stable_pattern','nodes':[{'id':'class','kind':'fallacy_pattern_collection','label':label}],'edges':[],'prototypes':[]}
        for p in selected:
            prefix=p['id']+':'
            graph['nodes'].append({'id':prefix+'prototype','kind':'pattern_prototype','constraints':deepcopy(p['constraints'])})
            graph['edges'].append({'src':'class','rel':'HAS_ALTERNATIVE_PROTOTYPE','dst':prefix+'prototype'})
            for node in p['graph']['nodes']:
                graph['nodes'].append({**deepcopy(node),'id':prefix+node['id']})
                graph['edges'].append({'src':prefix+'prototype','rel':'CONTAINS_PATTERN_NODE','dst':prefix+node['id']})
            for edge in p['graph']['edges']:
                graph['edges'].append({**deepcopy(edge),'src':prefix+edge['src'],'dst':prefix+edge['dst'],'article_support':p['positive_articles']})
            graph['prototypes'].append(deepcopy({k:v for k,v in p.items() if k!='graph'}))
        result[label]=graph
    return result
