"""Evaluate a frozen TRAIN bank on the official development split, without mining."""
import argparse
import hashlib
import json
import os
from core import ROOT,REPO,batch
from patterns_v2 import retrieve
from roundtrip_resume import extract
from verify_v2 import verify
from verify import metrics as selection_metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='dev_multires_oss120b_r1');p.add_argument('--split',choices=['dev','test'],default='dev');p.add_argument('--limit',type=int);p.add_argument('--plan',action='store_true');args=p.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.name):raise ValueError('Invalid name')
    os.environ.update(GRAPH_API_PROVIDER='market',GRAPH_MODEL_OVERRIDE='gpt-oss-120b',GRAPH_API_CONCURRENCY='4',GRAPH_MARKET_OUTPUT_MODE='prompt_json',GRAPH_API_INTERVAL='1')
    dev_path=REPO/('data/cocolofa/classification/'+args.split+'.json');bank_path=ROOT/'full_train_silver_multires_patterns_r1_stable_patterns.json'
    source_bytes=dev_path.read_bytes();bank_bytes=bank_path.read_bytes()
    samples=json.loads(source_bytes);bank=json.loads(bank_bytes)
    training=json.loads((ROOT/'full_train_span_fixed_r1_graphs.json').read_text(encoding='utf-8'))
    if {r['sample_id'] for r in training}&{s['sample_id'] for s in samples}:raise ValueError('TRAIN/development sample overlap')
    if args.limit is not None:
        if args.limit<=0:raise ValueError('Positive limit required')
        samples=samples[:args.limit]
    samples=[{**s,'split':'test' if args.split=='test' else 'development'} for s in samples]
    freeze={'evaluation_split':args.split,'bank_sha256':hashlib.sha256(bank_bytes).hexdigest(),'dev_sha256':hashlib.sha256(source_bytes).hexdigest(),'sample_ids':[s['sample_id'] for s in samples],'patterns':len(bank),'model':'gpt-oss-120b','matching_policy':'strict_and_core_for_all_labels_r1','mining_on_dev':False,'article_overlap_with_train':len({r['article_id'] for r in training}&{s['article_id'] for s in samples})}
    if args.plan:print(json.dumps(freeze,indent=2));return
    import msvcrt
    lock=open(ROOT/(args.name+'.run.lock'),'a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    freeze_path=ROOT/(args.name+'_freeze.json')
    if freeze_path.exists() and json.loads(freeze_path.read_text(encoding='utf-8'))!=freeze:raise ValueError('Frozen inputs changed; choose a new name')
    freeze_path.write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    print(f"Frozen {len(bank)} patterns; evaluating {len(samples)} {args.split} samples; 4 workers.",flush=True)
    def run(sample):
        graph=extract(sample,'gpt-oss-120b')
        candidates=retrieve(bank,graph)
        decision=verify(graph,sample,candidates)
        return {'sample_id':sample['sample_id'],'graph':graph,'candidates':candidates,'decision':decision}
    def save(rows):
        decisions=[r['decision'] for r in rows]
        summary={'expected':len(samples),'completed':len(rows),'complete':len(rows)==len(samples),'source_contract_valid':sum(r['graph']['status']=='accepted' for r in rows),'candidate_gold_recall':sum(any(c['label']==r['graph']['gold'] for c in r['candidates']) for r in rows)/len(rows) if rows else 0,'no_candidate':sum(not r['candidates'] for r in rows),'selection':selection_metrics(decisions) if decisions else {},'evaluation_split':args.split,'note':'Selection metrics include no-match and failed samples; no mining on the evaluation split.'}
        for suffix,value in [('_results.json',rows),('_metrics.json',summary)]:
            path=ROOT/(args.name+suffix);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
        return summary
    rows=batch(samples,run,'Frozen-bank '+args.split+' evaluation',workers=4,on_progress=save)
    print(json.dumps(save(rows),indent=2),flush=True);lock.close()

if __name__=='__main__':main()
