"""One additional extraction per flagged graph; preserve the previous snapshot."""
import json
import os
from collections import Counter
from core import ROOT, batch
from roundtrip_resume import extract, review, choose_existing, verbalize

NAME='full_train_problem_retry_once_r1'

def assessment(row):
    rt=row.get('roundtrip',{})
    return (rt.get('final') or rt.get('initial') or {}).get('assessment') or {}

def reasons(row):
    result=[]
    if not choose_existing(row):result.append('source_contract_failure')
    if row.get('roundtrip') and choose_existing(row) and not row['annotation']['applications']:result.append('empty_relations_after_review')
    if assessment(row).get('verdict')=='major':result.append('major_alignment')
    return result

def main():
    os.environ.update(GRAPH_API_PROVIDER='market',GRAPH_MODEL_OVERRIDE='gpt-oss-120b',GRAPH_API_CONCURRENCY='4',GRAPH_MARKET_OUTPUT_MODE='prompt_json',GRAPH_API_INTERVAL='1')
    import msvcrt
    lock=open(ROOT/(NAME+'.run.lock'),'a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    original=json.loads((ROOT/'full_train_market_gptoss120b_roundtrip_r1_graphs.json').read_text(encoding='utf-8'))
    samples={s['sample_id']:s for s in json.loads((ROOT/'full_train_manifest.json').read_text(encoding='utf-8'))['samples']}
    flagged=[r for r in original if reasons(r)]
    plan=[{'sample_id':r['sample_id'],'reasons':reasons(r)} for r in flagged]
    (ROOT/(NAME+'_selection.json')).write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(f'One additional generation for {len(flagged)} graphs; keeping {len(original)-len(flagged)} unchanged.',flush=True)
    def run(old):
        sample=samples[old['sample_id']]
        feedback={'retry_pass':'problem-graphs-once-r1','selection_reasons':reasons(old),'previous_assessment':assessment(old),'instruction':'Reconstruct once from source under the existing ontology. Preserve central offered reasoning, including pragmatic/implicit support. Empty relations are valid ONLY when no source-grounded relation is defensible; do not erase all edges merely to get alignment approval. Never invent a relation to fill a graph. Polarity means logical negation, not negative sentiment. Use only existing ontology kinds and warrant families.'}
        if old.get('graph') and old.get('annotation'):feedback['previous_reading']=verbalize(old)
        else:
            feedback['previous_status']=old['status']
        row=extract(sample,'gpt-oss-120b',feedback)
        if row.get('graph') is not None and row.get('annotation') is not None:
            checked=review(sample,row,'gpt-oss-120b')
            row['roundtrip']={'initial':checked,'regenerated':False}
        # A failed retry must not replace a previously contract-valid graph.
        selected=row if choose_existing(row) or not choose_existing(old) else old
        return {'sample_id':old['sample_id'],'reasons':reasons(old),'previous_status':old['status'],'previous_assessment':assessment(old),'attempt':row,'selected':selected,'retained_previous':selected is old}
    def save(results):
        replacements={r['sample_id']:r['selected'] for r in results}
        merged=[replacements.get(r['sample_id'],r) for r in original]
        metrics={'targeted':len(flagged),'completed':len(results),'complete':len(results)==len(flagged),'retry_contract_valid':sum(choose_existing(r['attempt']) for r in results),'retained_previous':sum(r['retained_previous'] for r in results),'retry_verdicts':dict(Counter(assessment(r['attempt']).get('verdict','unavailable') for r in results)),'retry_empty_relations':sum(choose_existing(r['attempt']) and not r['attempt']['annotation']['applications'] for r in results),'merged_contract_valid':sum(choose_existing(r) for r in merged),'total':len(merged)}
        for suffix,value in [('_attempts.json',results),('_graphs.json',merged),('_metrics.json',metrics)]:
            path=ROOT/(NAME+suffix);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
        return metrics
    results=batch(flagged,run,'Problem graph retry once',workers=4,on_progress=save)
    print(json.dumps(save(results),indent=2),flush=True)
    lock.close()

if __name__=='__main__':main()
