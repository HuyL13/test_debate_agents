"""Retry only unresolved rows after literal span boundary repair."""
import json
import os
import hashlib
from collections import Counter
from copy import deepcopy
from core import ROOT, invoke, batch
from ontology_v2 import source_units
from decomposed_source_v2 import prepare_propositions, process
from roundtrip_resume import choose_existing, review

NAME='full_train_span_fixed_r1'

def main():
    os.environ.update(GRAPH_API_PROVIDER='market',GRAPH_MODEL_OVERRIDE='gpt-oss-120b',GRAPH_API_CONCURRENCY='4',GRAPH_MARKET_OUTPUT_MODE='prompt_json',GRAPH_API_INTERVAL='1')
    import msvcrt
    lock=open(ROOT/(NAME+'.run.lock'),'a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    original=json.loads((ROOT/'full_train_problem_retry_once_r1_graphs.json').read_text(encoding='utf-8'))
    samples={s['sample_id']:s for s in json.loads((ROOT/'full_train_manifest.json').read_text(encoding='utf-8'))['samples']}
    failed=[r for r in original if not choose_existing(r)]
    print(f'Keeping {len(original)-len(failed)} graphs unchanged; repairing {len(failed)} failed rows.',flush=True)
    def run(old):
        sample=samples[old['sample_id']];units=source_units(sample);replayed=False
        def call(*args,**kwargs):
            nonlocal replayed
            if args[1]=='source_propositions_v2' and old['status']=='proposal_failed':
                cid=old['stage_call_ids']['proposal'];previous=json.loads((ROOT/'calls'/(cid+'.json')).read_text(encoding='utf-8'))
                for attempt in reversed(previous['attempts']):
                    raw=attempt.get('output')
                    if raw is None:continue
                    try:prepare_propositions(raw,units)
                    except (ValueError,TypeError,KeyError):continue
                    new_id=hashlib.sha256((cid+'span-boundary-revalidation-r1').encode()).hexdigest()[:24]
                    rec=deepcopy(previous);rec.update(call_id=new_id,status='accepted',output=raw,version=previous['version']+'-span-revalidated-r1',local_revalidation={'original_call_id':cid,'reason':'Corrected punctuation boundaries; original API output unchanged.','new_source_units':units})
                    (ROOT/'calls'/(new_id+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8');replayed=True
                    return rec
                args=list(args)
                args[3]+='\nREPAIR: Prior literal output could not pass the current source validator. A recommendation must have event_role action or none, never outcome. Keep exact original source words and do not remove negation. Return a complete corrected proposition set.'
                args[4]={**args[4],'repair_pass':'span-fixed-proposition-r1'}
            if old['status']=='witness_failed':
                args=list(args);args[3]+='\nREPAIR CONSTRAINT: The title is context for resolving references, not an author-used premise. Do not invent adoption from applause. Reconstruct the comment own reasoning; do not connect a contextual title as an initial event to an epistemic question. An uncertainty about effects is not itself an event outcome.'
                args[4]={**args[4],'repair_pass':'span-fixed-context-r1'}
            return invoke(*args,**kwargs)
        row=process(sample,model='gpt-oss-120b',fewshot=True,warrant_mode='slots',invoke_fn=call)
        row['span_fix_retry']={'previous_status':old['status'],'propositions_revalidated_without_api':replayed}
        if row.get('graph') is not None and row.get('annotation') is not None:row['roundtrip']={'initial':review(sample,row,'gpt-oss-120b'),'regenerated':False}
        return row
    def save(results):
        replacement={r['sample_id']:r for r in results};merged=[replacement.get(r['sample_id'],r) for r in original]
        metrics={'targeted':len(failed),'completed':len(results),'complete':len(results)==len(failed),'retry_statuses':dict(Counter(r['status'] for r in results)),'propositions_revalidated_without_api':sum(r['span_fix_retry']['propositions_revalidated_without_api'] for r in results),'merged_contract_valid':sum(choose_existing(r) for r in merged),'total':len(merged)}
        for suffix,value in [('_attempts.json',results),('_graphs.json',merged),('_metrics.json',metrics)]:
            path=ROOT/(NAME+suffix);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
        return metrics
    results=batch(failed,run,'Span-fixed retry',workers=4,on_progress=save)
    print(json.dumps(save(results),indent=2),flush=True);lock.close()

if __name__=='__main__':main()
