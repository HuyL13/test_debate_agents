"""Executable V2 source -> train patterns -> candidates -> scored selection."""
import argparse
import json
import os
from core import ROOT,REPO,batch,render_report
from pipeline import dataset
from pipeline_v2 import run_source
from patterns_v2 import mine_patterns,bootstrap_recovery,retrieve
from verify_v2 import verify
from verify import metrics as selection_metrics


def pattern_stage(rows):
    training=[r for r in rows if r.get('split')=='induction']
    if not training:raise ValueError('explicit induction rows required; never learn patterns from evaluation rows')
    patterns=mine_patterns(training);recovery=bootstrap_recovery(patterns,training)
    for p in patterns:p['bootstrap_recovery']=recovery[p['id']]
    stable=[p for p in patterns if p['bootstrap_recovery']>=.8]
    merged={}
    for label in sorted({r['gold'] for r in training}):
        own=[p for p in stable if p['label']==label];prototypes=[];nodes=[];edges=[]
        for p in own:
            for proto in p['prototypes']:
                prefix=p['id']+'/'+proto['id']+'/'
                prototypes.append({'pattern_id':p['id'],**proto})
                nodes.extend({**n,'id':prefix+n['id']} for n in proto['graph']['nodes'])
                edges.extend({**e,'src':prefix+e['src'],'dst':prefix+e['dst']} for e in proto['graph']['edges'])
        merged[label]={'label':label,'status':'supported' if own else 'insufficient_supported_patterns',
                       'composition':'alternative_prototypes_no_cross_paths','prototypes':prototypes,'graph':{'nodes':nodes,'edges':edges}}
    retrieval=[{'sample_id':r['sample_id'],'gold':r['gold'],'split':r['split'],'source_status':r['status'],'candidates':retrieve(stable,r)} for r in rows if r.get('split')!='induction']
    metrics={}
    for split in sorted({r['split'] for r in retrieval}):
        rs=[r for r in retrieval if r['split']==split]
        def summary(pool):
            return {'count':len(pool),'candidate_gold_recall':sum(any(c['label']==r['gold'] for c in r['candidates']) for r in pool)/len(pool) if pool else 0,
                    'no_candidate':sum(not r['candidates'] for r in pool)}
        metrics[split]={**summary(rs),'per_label':{label:summary([r for r in rs if r['gold']==label]) for label in sorted({r['gold'] for r in rs})}}
    metrics['retrieval_budget']={'max_distinct_labels':3,'max_subgraphs_per_label':3,'recall_definition':'gold label present among top3 label hypotheses; each label retains up to3 distinct source subgraphs for comparative verification'}
    metrics['induction']={'count':len(training),'source_contract_valid':sum(r['status']=='accepted' for r in training),'tentative_patterns':len(patterns),'stable_patterns':len(stable),
                          'labels_without_stable_patterns':[label for label,m in merged.items() if m['status']!='supported']}
    return {'patterns':patterns,'stable_patterns':stable,'merged_pattern_graphs':merged,'retrieval':retrieval,'metrics':metrics}


def run_experiment(rows,name,repeat=0,do_verify=True,workers=2):
    result=pattern_stage(rows)
    for field in ['patterns','stable_patterns','merged_pattern_graphs','retrieval']:
        (ROOT/(name+'_'+field+'.json')).write_text(json.dumps(result[field],ensure_ascii=False,indent=2),encoding='utf-8')
    decisions=[]
    if do_verify:
        sources={s['sample_id']:s for s in json.loads((REPO/'data/cocolofa/classification/train.json').read_text(encoding='utf-8'))}
        byid={r['sample_id']:r for r in rows}
        def run(r):return verify(byid[r['sample_id']],sources[r['sample_id']],r['candidates'],repeat)
        def checkpoint(partial):
            (ROOT/(name+'_evaluations.json')).write_text(json.dumps(partial,ensure_ascii=False,indent=2),encoding='utf-8')
        decisions=batch(result['retrieval'],run,'V2 candidate verification',workers=workers,on_progress=checkpoint) if result['retrieval'] else []
        (ROOT/(name+'_evaluations.json')).write_text(json.dumps(decisions,ensure_ascii=False,indent=2),encoding='utf-8')
        result['metrics']['selection']={split:selection_metrics([r for r in decisions if r['split']==split]) for split in sorted({r['split'] for r in decisions})}
    result['metrics']['verification_executed']=do_verify
    (ROOT/(name+'_metrics.json')).write_text(json.dumps(result['metrics'],ensure_ascii=False,indent=2),encoding='utf-8')
    # Source stage reports retain all raw source calls; this report focuses on
    # native patterns, candidate mappings and final selection.
    call_ids={cid for row in rows for cid in row.get('stage_call_ids',{}).values() if cid}
    call_ids.update(d['verification_call_id'] for d in decisions if d.get('verification_call_id'))
    render_report(ROOT/(name+'_report.html'),{**result,'evaluations':decisions},result['metrics'],call_ids)
    return result,decisions


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-examples',action='store_true');p.add_argument('--source-model',default='nvidia/nemotron-3-super-120b-a12b');p.add_argument('--warrant-mode',choices=['roles','slots'],default='roles');p.add_argument('--source-mode',choices=['joint','decomposed','faceted'],default='joint');p.add_argument('--graphs');p.add_argument('--name',default='experiment_v2');p.add_argument('--induction',type=int,default=20);p.add_argument('--development-per-label',type=int,default=10);p.add_argument('--repeat',type=int,default=0);p.add_argument('--interval',type=float,default=12);p.add_argument('--workers',type=int,default=2);p.add_argument('--no-verify',action='store_true');args=p.parse_args()
    if args.interval<=0:raise ValueError('positive API interval required')
    os.environ['GRAPH_API_INTERVAL']=str(args.interval)
    if args.graphs:rows=json.loads((ROOT/args.graphs).read_text(encoding='utf-8'))
    else:
        if not 1<=args.development_per_label<=10:raise ValueError('development sample size must be1..10per label')
        splits=dataset(args.induction);dev=[]
        for label in sorted({s['gold'] for s in splits['development']}):dev.extend([s for s in splits['development'] if s['gold']==label][:args.development_per_label])
        samples=splits['induction']+dev
        (ROOT/(args.name+'_partitions.json')).write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
        rows,_=run_source(samples,args.name+'_source_r'+str(args.repeat),args.repeat,True,args.workers,args.source_mode,args.warrant_mode,args.source_model,args.source_examples)
    result,_=run_experiment(rows,args.name,args.repeat,not args.no_verify,args.workers)
    print(json.dumps(result['metrics'],indent=2),flush=True)


if __name__=='__main__':main()
