"""Mine equally at strict and core resolutions; no API or held-out data."""
import json
from collections import Counter
from core import ROOT
from patterns_v2 import mine_patterns,bootstrap_recovery,application_subgraph,_key

NAME='full_train_silver_multires_patterns_r1'

def main():
    rows=json.loads((ROOT/'full_train_span_fixed_r1_graphs.json').read_text(encoding='utf-8'))
    if any(r.get('split')!='induction' for r in rows):raise ValueError('Only induction TRAIN rows allowed')
    patterns=[]
    for resolution in ['strict','core']:
        found=mine_patterns(rows,resolution=resolution)
        print(f'{resolution}: {len(found)} tentative patterns',flush=True);patterns.extend(found)
    recovery=bootstrap_recovery(patterns,rows)
    for p in patterns:p['bootstrap_recovery']=recovery[p['id']]
    stable=[p for p in patterns if p['bootstrap_recovery']>=.8]
    byid={r['sample_id']:r for r in rows};checks=0
    for p in stable:
        for w in p['witnesses']:
            graph,mapping=application_subgraph(byid[w['sample_id']],w['application_index'],p['resolution'])
            if _key(graph)!=p['signature'] or mapping!=w['mapping']:raise ValueError('Witness does not reproduce its actual prototype')
            checks+=1
    labels=sorted({r['gold'] for r in rows})
    merged={label:{'label':label,'composition':'alternative_prototypes_no_cross_paths','prototypes':[{'pattern_id':p['id'],'resolution':p['resolution'],**proto} for p in stable if p['label']==label for proto in p['prototypes']]} for label in labels}
    metrics={'policy':'strict_and_core_for_all_labels_r1','tier':'automatic_silver','train_graphs':len(rows),'tentative_patterns':len(patterns),'stable_patterns':len(stable),'thresholds':{'min_distinct_articles':5,'min_purity':.45,'min_bootstrap':.8,'bootstrap_rounds':30,'max_tentative_per_label_per_resolution':6},'per_label':{label:dict(Counter(p['resolution'] for p in stable if p['label']==label)) for label in labels},'labels_without_stable_patterns':[label for label in labels if not merged[label]['prototypes']],'witnesses_revalidated':checks,'verification_executed':False,'heldout_evaluation_executed':False}
    for suffix,value in [('_patterns.json',patterns),('_stable_patterns.json',stable),('_merged_pattern_graphs.json',merged),('_metrics.json',metrics)]:
        path=ROOT/(NAME+suffix);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
    print(json.dumps(metrics,indent=2),flush=True)

if __name__=='__main__':main()
