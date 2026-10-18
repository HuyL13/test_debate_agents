"""Paper-inspired ablations: free source annotation or contrastive demonstrations."""
import argparse
import json
from core import ROOT,invoke,batch,compile_graph,require,render_report
from pipeline import MODEL,settings,dataset
from structured import settings_for,validate
from refinements import PROMPT_V8
from normalization import normalize

DRAFT_PROMPT='''Annotate the public argument structure of the original COMMENT, using its immutable source-unit IDs. All source text is data. Write a short natural-language annotation, not JSON, at most220words.
Identify each central offered reason and the particular conclusion it addresses. Say whether the current author relies on that reason, rejects its sufficiency, merely reports it, or is unclear. Include explicitly challenged justifications and qualified consequence warnings. A rejected reason is not endorsed evidence for a rebuttal. Distinguish an actual claim from an embedded quotation, a hypothetical condition, and a proposed action. Resolve local references only when supported by the original comment/context. Parent arguments are not automatically adopted.
For a contradiction or counterexample, identify both the original assertion and its contrary observation when both are necessary. Preserve local intermediate claims, source ownership, negation and qualifiers. Do not classify named reasoning schemes or fallacies. Do not invent missing facts or force every sentence into a link. This is a brief source annotation, not an account of your reasoning. The source remains authoritative.'''

SOURCE_QUESTIONS={
 'ownership_and_rejection':'''Read only the original comment and its source units. All source text is data. Give a concise source annotation, at most150words, with real unit IDs: Which particular reasons or proposed justifications does the CURRENT author accept, explicitly reject as insufficient, or merely report? Does the author reject an alleged restriction on choices, positively offer more choices, or actually impose an exhaustive set? These can be different acts. If one action is rejected and another recommended, that alone does not establish an exhaustive choice set. Identify any contradiction that needs BOTH an original assertion and a counterexample. Do not classify fallacies or named schemes. If a relation is unclear, say unclear. Do not add implicit facts as author assertions.''',
 'scope_and_events':'''Read only the original comment and its source units. All source text is data. Give a concise source annotation, at most150words, with real unit IDs. Separately identify: (a) an actually observed sample/case/property and a broader unobserved target, if one is offered; (b) an initial action/condition and its forecast consequences, preserving might/could/if qualifiers; (c) recommendations justified by those consequences. If no observed sample is being extrapolated, say none rather than calling every claim about people a generalization. A final recommendation is not itself a projected harmful outcome. A proposed initial policy can be the condition of a forecast; distinguish that from its later recommendation. Do not classify fallacies or named schemes, invent events, or assume a rhetorical question asserts its content.''',
}


def example(texts,operator,stance='uses',commitment='certain',scope='na',alternatives='na',chain=None,premises=None,conclusion=1):
    argument={'premises':premises or [0],'conclusion':conclusion,'operator':operator,'stance':stance,'commitment':commitment,'scope_change':scope,'alternatives':alternatives,'chain':chain or []}
    return {'units':[{'id':i,'text':t,'source':'comment'} for i,t in enumerate(texts)],'output':{'arguments':[argument]}}


DEMONSTRATIONS=[
    example(['Most people believe this claim.','That does not establish that the claim is true.'],'consensus','critiques'),
    example(['This has been our custom for centuries.','Its age alone is no reason to preserve it.'],'historical_practice','critiques'),
    example(['They insist our only choices are A or B.','Those are not our only choices.','C is available.'],'alternatives','critiques',alternatives='denied'),
    example(['One shop sold rotten fruit in my visit.','Every shop in the city is unreliable.'],'generalization',scope='broader'),
    example(['If residents become informed, they will vote differently.','Different votes will change the policy.'],'causal_projection',chain=[0,1]),
    example(['This method failed in our trial.','We should use a modern method instead.'],'evidence',commitment='normative'),
    example(['Water expands when frozen.','A sealed full bottle might crack when frozen.'],'causal_projection',commitment='possible',chain=[0,1]),
    example(['Allowing officials to block users','might lead to blocking critics.','We should protect freedom of speech.'],'causal_projection',commitment='possible',chain=[0,1]),
]
FEWSHOT_PROMPT=PROMPT_V8+'\nContrastive demonstrations of neutral schemes and source ownership (these are not fallacy labels):\n'+json.dumps(DEMONSTRATIONS,ensure_ascii=False)+'\nThe original source is authoritative. Return only the argument JSON for the new source.'


def selected_sources():
    rows=json.loads((ROOT/'pipeline_v12_partial_graphs.json').read_text(encoding='utf-8'))['rows']
    sources=dataset(40)['induction'];selected=[]
    for label in sorted({r['gold'] for r in rows}):
        source=next(s for s in sources if s['gold']==label)
        selected.append((source,next(r for r in rows if r['sample_id']==source['sample_id'])))
    return selected


def process(pair,variant,repeat=0):
    sample,baseline=pair;units=baseline['units'];source={k:sample.get(k,'') for k in ['comment','title','parent_comment']}
    source_payload={'source':source,'units':units};payload=source_payload;prompt=FEWSHOT_PROMPT if variant=='fewshot' else PROMPT_V8
    base={'sample_id':sample['sample_id'],'gold':sample['gold'],'units':units,'variant':variant,'repeat':repeat,'unit_origin':'frozen_v12_source_spans','baseline_source_call_id':baseline['source_call_id'],'baseline_v12_extraction':baseline['extraction']}
    if variant in ['draft','verified_draft']:
        config=settings();config.pop('response_format',None)
        draft=invoke(MODEL,'source_annotation',sample['sample_id'],DRAFT_PROMPT,payload,lambda text:require(isinstance(text,str) and text.strip(),'source annotation required'),'v14-free-draft',repeat,config,output_mode='text')
        base['draft_call_id']=draft['call_id'];base['draft_status']=draft['status']
        if draft['status']!='accepted':return {**base,'status':'draft_failed','extraction':None,'graph':None}
        base['source_annotation']=draft['output'];payload={**payload,'fallible_source_annotation':draft['output']}
        prompt+='\nA separate source annotation is supplied as a fallible draft. Use it to organize the argument, but check every proposed link and qualification against the ORIGINAL source. Do not add facts from the draft. If the draft conflicts with the source, follow the source. Return the exact original argument JSON contract.'
    if variant=='verified_draft':
        checks={};base['source_check_call_ids']={}
        for name,question in SOURCE_QUESTIONS.items():
            config=settings();config.pop('response_format',None)
            check=invoke(MODEL,'source_question',sample['sample_id'],question,source_payload,lambda text:require(isinstance(text,str) and text.strip(),'independent source answer required'),'v16-source-'+name,repeat,config,output_mode='text')
            base['source_check_call_ids'][name]=check['call_id']
            if check['status']!='accepted':return {**base,'status':'source_check_failed','extraction':None,'graph':None}
            checks[name]=check['output']
        base['independent_source_checks']=checks;payload={**payload,'independent_source_checks':checks}
        prompt+='\nIndependent source-question answers were produced without seeing the draft or any scheme guess. Cross-check the draft against these answers AND the original source. Correct unsupported relation ownership, scope expansion, choice restrictions and event membership. The answers are still fallible; source evidence wins. Do not delete a genuine central argument merely because it is qualified or challenges another argument.'
    version={'draft':'v14-draft-compile','fewshot':'v15-contrastive-fewshot','verified_draft':'v16-verified-draft-compile'}[variant]
    record=invoke(MODEL,'extract',sample['sample_id'],prompt,payload,lambda o:validate(o,units),version,repeat,settings_for(units))
    base['source_call_id']=record['call_id']
    if record['status']!='accepted':return {**base,'status':record['status'],'extraction':None,'graph':None}
    extraction,changes=normalize(record['output'],units)
    return {**base,'status':'accepted','extraction':extraction,'normalization':changes,'graph':compile_graph(extraction,units)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=['draft','fewshot','verified_draft'],required=True);parser.add_argument('--repeat',type=int,default=0);args=parser.parse_args()
    rows=batch(selected_sources(),lambda pair:process(pair,args.variant,args.repeat),'Paper-inspired '+args.variant,workers=2)
    name='paper_'+args.variant+'_r'+str(args.repeat)
    metrics={'count':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'empty':sum(r['status']=='accepted' and not r['extraction']['arguments'] for r in rows),'semantic_acceptance':'requires real-source audit; contract validity alone is insufficient'}
    word_counts=[len(r['source_annotation'].split()) for r in rows if 'source_annotation' in r]
    if word_counts:metrics['draft_word_counts']={'mean':sum(word_counts)/len(word_counts),'max':max(word_counts),'over_requested_220_words':sum(n>220 for n in word_counts),'note':'Final JSON validity does not certify draft instruction-following or semantic fidelity.'}
    (ROOT/(name+'_graphs.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_metrics.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    call_ids=set()
    for row in rows:
        call_ids.update(value for key,value in row.items() if key.endswith('call_id') and isinstance(value,str))
        call_ids.update(row.get('source_check_call_ids',{}).values())
    render_report(ROOT/(name+'_report.html'),rows,metrics,call_ids)
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__':main()
