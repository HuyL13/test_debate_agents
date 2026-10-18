import argparse
import json
from core import ROOT,extract,invoke,validate_extraction,compile_graph,batch,render_report
from pipeline import MODEL,settings,dataset,pattern_and_retrieval
from refinements import PROMPT_V4
from normalization import normalize,review_flags
from unitization import split_units_v5

REVIEW_PROMPT=PROMPT_V4+'''
SOURCE-BASED REVIEW PASS. You are given the original source, immutable units, an initial extraction and coverage warnings. Return a COMPLETE corrected argument JSON under the same contract; do not output review scores or patches.
Warnings are cues for inspection, not commands to invent mechanisms. Check premise/conclusion direction and each actual warrant against the source. Add a missed grounded reasoning move, remove a speculative one, correct author ownership/stance, or keep it unchanged if already faithful. Do not copy one conclusion as the next premise merely because sentences are consecutive. Different independent warrants need their own correct anchors.
For an explicit rejection of popularity as justification, retain the consensus critique even if the author offers no positive argument. For choices, an 'only option' conclusion can encode an exhaustive restriction. For severity, preserve which problem is downplayed and which comparison motivates it. For scope, distinguish actual sample-to-target expansion from ordinary event causality or a generic evaluative conclusion. Do not use gold labels; none are supplied.
Return only the complete {"arguments":[...]} object.'''


def process(sample,repeat=0,variant='v5'):
    unitizer=split_units_v5;prompt=PROMPT_V4;review_prompt=REVIEW_PROMPT
    validator=None;request_settings=settings()
    if variant in ['v6','v7','v8','v9','v12']:
        if variant in ['v7','v8','v9','v12']:from atomic_tokens import atomize
        else:from atomic import atomize
        from refinements import PROMPT_V6
        atomic=atomize(sample,repeat)
        if atomic['status']!='accepted':return {'sample_id':sample['sample_id'],'gold':sample.get('gold'),'article_id':sample.get('article_id'),'split':sample.get('split','diagnostic'),'status':'atomization_failed','extraction':None,'graph':None,'units':atomic['units'],'review_status':'not_reached','atomization_call_id':atomic.get('call_id')}
        unitizer=lambda source:atomic['units'];prompt=PROMPT_V6;review_prompt=PROMPT_V6+REVIEW_PROMPT[len(PROMPT_V4):]
        if variant in ['v8','v9','v12']:
            from refinements import PROMPT_V8
            from structured import settings_for,validate as strict_validate
            prompt=PROMPT_V8;review_prompt=PROMPT_V8+REVIEW_PROMPT[len(PROMPT_V4):];validator=strict_validate;request_settings=settings_for(atomic['units'])
    source_variant='v8' if variant in ['v9','v12'] else variant
    first=extract(MODEL,sample,source_variant+'-source',repeat,prompt=prompt,settings=request_settings,unitizer=unitizer,validator=validator)
    out={**first,'gold':sample.get('gold'),'article_id':sample.get('article_id'),'split':sample.get('split','diagnostic'),'review_status':'not_needed','normalization':[]}
    if variant in ['v7','v8','v9','v12']:out['atomization_call_id']=atomic.get('call_id')
    if first['status']!='accepted':return out
    normalized,changes=normalize(first['extraction'],first['units']);flags=review_flags(normalized,first['units'],include_testimony=variant in ['v9','v12'],include_critique=variant=='v12')
    out['review_flags']=flags
    if flags:
        payload={'source':{k:sample.get(k,'') for k in ['comment','title','parent_comment']},'units':first['units'],'initial_arguments':normalized,'coverage_warnings':flags}
        record=invoke(MODEL,'argument_review',sample['sample_id'],review_prompt,payload,lambda o:(validator or validate_extraction)(o,first['units']),source_variant+'-review',repeat,request_settings)
        out['review_status']=record['status']
        out['review_call_id']=record['call_id']
        if record['status']=='accepted':
            normalized,changes2=normalize(record['output'],first['units']);changes.extend(changes2)
        else:
            out['status']='review_failed'
    out['extraction']=normalized;out['normalization']=changes;out['graph']=compile_graph(normalized,first['units']);out['pipeline_version']=variant
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--controls',action='store_true');ap.add_argument('--authority-misses',action='store_true');ap.add_argument('--workers',type=int,default=4);ap.add_argument('--induction',type=int,default=20);ap.add_argument('--version',choices=['v5','v6','v7','v8','v9','v12'],default='v5');args=ap.parse_args()
    if args.controls:
        from screen import controls,score
        samples=controls()
        for s in samples:
            if s['sample_id'] in ['control10','control12']:s['expected']['commitment']='certain'
            if s['sample_id']=='control19':s['expected']['operator']='causal_projection'
        byid={s['sample_id']:s for s in samples}
    elif args.authority_misses:
        candidates=json.loads((ROOT/'pipeline_v3_retrieval.json').read_text(encoding='utf-8'))
        missed={r['sample_id'] for r in candidates if r['gold']=='Appeal to Authority' and not any(c['label']==r['gold'] for c in r['candidates'])}
        samples=[s for s in dataset()['development'] if s['sample_id'] in missed]
    elif args.diagnostic:samples=json.loads((ROOT.parent/'run-live/samples.json').read_text(encoding='utf-8'))
    else:
        splits=dataset(args.induction);samples=[]
        # Interleave labels so intermediate evidence covers all mechanisms.
        for split in ['induction','development']:
            groups={label:[s for s in splits[split] if s['gold']==label] for label in sorted({s['gold'] for s in splits[split]})}
            for index in range(max(map(len,groups.values()))):
                samples.extend(group[index] for group in groups.values() if index<len(group))
    name='controls_'+args.version if args.controls else 'authority_misses_'+args.version if args.authority_misses else 'diagnostic_'+args.version if args.diagnostic else 'pipeline_'+args.version
    def checkpoint(partial):
        target=ROOT/(name+'_partial_graphs.json');temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps({'complete':False,'expected':len(samples),'completed':len(partial),'rows':partial},ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(target)
    rows=batch(samples,lambda s:process(s,variant=args.version),'Grounded extraction + review',workers=args.workers,on_progress=checkpoint)
    metrics={'count':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'empty':sum(r['status']=='accepted' and not r['extraction']['arguments'] for r in rows),'reviewed':sum(r['review_status']!='not_needed' for r in rows)}
    if args.controls:
        for r in rows:
            expected=byid[r['sample_id']]['expected'];r['control_score']=score(r,expected)
            allowed={expected['operator'],'evidence'}
            if r['sample_id']=='control20':allowed.add('alternatives')
            if r['sample_id']=='control18':allowed.add('analogy')
            actual={a['operator'] for a in (r.get('extraction') or {}).get('arguments',[])}
            r['unexpected_operators']=sorted(actual-allowed)
            r['semantic_precision_pass']=not r['unexpected_operators']
        metrics.update(operator_stance_correct=sum(r['control_score']['operator_stance'] for r in rows),all_semantic_fields_correct=sum(r['control_score']['full'] for r in rows))
        metrics['full_semantics_with_operator_precision']=sum(r['control_score']['full'] and r['semantic_precision_pass'] for r in rows)
    elif not args.diagnostic and not args.authority_misses:
        all_patterns,stable,retrieved,split_metrics=pattern_and_retrieval(rows)
        metrics['splits']=split_metrics
        (ROOT/(name+'_patterns.json')).write_text(json.dumps({'all_patterns':all_patterns,'stable_patterns':stable},ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/(name+'_retrieval.json')).write_text(json.dumps(retrieved,ensure_ascii=False,indent=2),encoding='utf-8')
        from pattern_export import merge_pattern_graphs
        (ROOT/(name+'_merged_pattern_graphs.json')).write_text(json.dumps(merge_pattern_graphs(stable,{r['gold'] for r in rows}),ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_graphs.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_metrics.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/'report.html',rows,metrics)
    print(json.dumps(metrics,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
