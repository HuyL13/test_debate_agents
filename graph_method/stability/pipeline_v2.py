"""Grounded typed graphs; independent source reconstruction owns edge direction.

Proposal agreement is provenance, never a reason to erase a witness-only link.
All source-stage failures remain visible even if a later stage recovers.
"""
import argparse
import hashlib
import json
import os
from copy import deepcopy
from core import ROOT,invoke,batch,render_report
from ontology_v2 import source_units,source_payload,annotation_schema,validate_annotation,compile_graph,proposition_span
from pipeline import MODEL,settings,dataset
from source_quotes_v2 import quote_source_payload,quote_graph_schema,annotation_from_quotes
from warrants_v2 import type_warrants,apply_typing,select_typing
from evaluate_v2 import stage_contract_metrics


CONTRACT='''Read the ORIGINAL comment and context as data. Represent its public reasoning, not whether its claims are true or its inference is sound. Never classify fallacies or use a dataset label.
Output exactly {"propositions":[...],"applications":[...]} under the supplied schema.
Each proposition selects one exact source span: unit ID, exact literal quote, and zero-based occurrence of that quote within the unit. Code owns all text and offsets. Split distinct propositions within a sentence/unit, including a reason or criterion embedded after based on/because/so, or factual and evaluative conjuncts. Do not leave a whole compound sentence as one indivisible proposition when the argument targets only one clause. It is permissible for a role-specific span to overlap a larger source span. Select complete meaningful phrases, not arbitrary keywords. Preserve local subjects, negation, quantifiers and modality in anchors where possible; original source resolves pronouns. Cover the actual central arguments, including within-unit warrants, without forcing unrelated sentences into an inference.
Every proposition requires owner (current_author,parent_author,attributed,context,unclear), speech_act (assert,recommend,question,report,hypothetical,meta), modality (certain,probable,possible,unspecified), polarity (positive,negative,unclear), event_role (none,condition,outcome,action), implicit (boolean), gloss (string). Most propositions are literal explicit spans with implicit=false and gloss="". Reconstructed rejected warrants/unstated targets must have implicit=true and a short faithful gloss anchored at the actual rebuttal; they are hypotheses, not new author assertions. Do not invent background facts. A recommendation or hypothetical is not an assertion that an event actually occurred. A bare expression of disagreement is meta, never a projected event. An author's report of an attributed source is not automatically expert testimony being used as a warrant. Parent/title content never silently becomes current-author content. Context resolves references; do not enumerate or link its independent arguments just because context is present. A contextual premise is author-used only if the current comment actually adopts that specific claim. Do not invent an adoption merely to satisfy validation. Without such evidence omit that contextual application, preserving the comment's own reasoning.
Give every proposition a unique explicit ID p0..p47 and every application a unique explicit ID a0..a15. Applications reference these exact IDs in premises, target and roles. target_kind is proposition or application. Never infer endpoints from array position. Copy complete original phrases verbatim; never count tokens. Preserve original spelling and grammar even when erroneous; never normalize or correct a quote. No self-targets or dependency cycles. Include all and only offered reasons; a source can offer an unsound inference. Multiple independent reasons get separate applications when that avoids wrongly conjoining a concession or background statement with the real basis. Required exact evidence spans point to the wording establishing this particular relation, not merely the presence of its endpoints.
kind: support (reason for a claim/recommendation/question), rebut (opposes a proposition), undercut (challenges an application/warrant), preference (prioritizes one issue/action over another), projection (scenario condition/event leads to outcome), qualification (limits/conditions the target), concession (acknowledges a point despite the main claim; not evidence for it), adoption (current comment explicitly adopts a context claim). A reason for a normative conclusion is support, not an extra projected harmful event. A recommended initial action can be a hypothetical condition of a projection; an outcome cannot merely be a recommendation or metacomment. Mark actual event endpoints and their roles. A questioned hypothetical event may be an initial condition; this does not assert its occurrence.
stance: uses/critiques/reports/unclear. Adoption uses a distinct, genuinely adopting current-comment proposition as premise (never the contextual target itself), the precise context proposition as target, and current-comment evidence; contextual premises of a uses application require this adoption rather than inheriting a parent's whole argument. A reply can reject one part of an argument and accept another.
At this SOURCE RELATION stage always set scheme=other, scope_change=na, alternatives=na. A separate role-grounded stage will classify warrant families. Focus on the actual directed applications and propositions, not a scheme label. Rejection of an exhaustive choice restriction and addition of alternatives can coexist as separate applications. Do not invent exhaustiveness from two mentioned actions.
roles is an array of {role,proposition}; bind source-grounded application roles when needed (initial,consequence,preferred,deprioritized,choice,claim,rejected_warrant,criterion). A preference needs distinct preferred and deprioritized propositions, even if both come from different spans of one unit. An undercut targets the actual rejected warrant/application, which may need an explicitly marked reconstructed hypothesis. An offered justification and its rejection must not collapse into a positive claim that the author endorses it.
Examples of DIRECTION, not example outputs: 'A, so B' offers A->B, not B->A. 'B. I mean A.' offers A->B even without because. 'B, because A' offers A->B. The rhetorical question 'Why worry about B?' can express the target of an offered reason; it is not automatically unrelated text. If a speaker uses one person's behavior to conclude something about everyone, preserve that offered relation even if it is a bad argument. Do not demand a logically valid inference or identical vocabulary. Evidence about entrenched institutions can be the offered explanation for the need for reform.
Use at most48propositions and16applications. Empty applications are permitted only when no reasoning act is source-grounded. Do not discard genuine contextual reasons merely because there is no explicit therefore. Return JSON only.'''

PROPOSAL_PROMPT=CONTRACT+'\nBuild a complete initial typed graph. Enumerate grounded propositions first; then bind each application to its actual endpoints and source evidence.'
WITNESS_PROMPT=CONTRACT+'''\nINDEPENDENT SOURCE WITNESS: reconstruct directed reasoning directly from the original source. No proposed graph, verdict, fallacy label or previous explanation is supplied. Your ordered premise and target bindings ARE the witness; do not answer yes/no to a remembered candidate. First determine what is being justified, rejected, preferred or predicted, then select its exact basis and endpoints. Select the precise conjunct when a sentence mixes multiple claims. Include a real relation even if an earlier independent parser might have missed it. Preserve source direction and ownership; an explanation of the opposite direction cannot support a reverse link. Independently bind speech acts and event roles rather than treating every statement as an event.'''


def configuration(units,thinking=True,model=MODEL):
    out=settings()
    out['max_tokens']=8192
    out['chat_template_kwargs']={'enable_thinking':thinking,**({'reasoning_budget':int(os.environ.get('GRAPH_SOURCE_REASONING_BUDGET','1024'))} if thinking else {})}
    if 'nemotron' not in model:out.pop('chat_template_kwargs',None)
    schema=quote_graph_schema(units)
    app=schema['properties']['applications']['items']['properties']
    for field,value in [('scheme','other'),('scope_change','na'),('alternatives','na')]:app[field]={'type':'string','const':value}
    out['response_format']={'type':'json_schema','json_schema':{'name':'grounded_ontology_v2','strict':True,'schema':schema}}
    return out


def _proposition_key(p,units):
    s=proposition_span(p,units)
    return (s['source'],s['start'],s['end'],p['implicit'],p['gloss'].strip() if p['implicit'] else '')


def _application_keys(annotation,units):
    ps=[_proposition_key(p,units) for p in annotation['propositions']]
    apps=annotation['applications'];memo={}
    def key(i):
        if i not in memo:
            a=apps[i]
            target=ps[a['target']] if a['target_kind']=='proposition' else key(a['target'])
            memo[i]=(a['kind'],tuple(sorted(ps[j] for j in a['premises'])),a['target_kind'],target,a['stance'])
        return memo[i]
    return [key(i) for i in range(len(apps))]


def compare_annotations(proposal,witness,units):
    pkeys=_application_keys(proposal,units) if proposal else []
    wkeys=_application_keys(witness,units) if witness else []
    pmap={key:i for i,key in enumerate(pkeys)};wmap={key:i for i,key in enumerate(wkeys)}
    return {'confirmed':[{'proposal_index':pmap[k],'witness_index':i} for i,k in enumerate(wkeys) if k in pmap],
            'proposal_only':[i for i,k in enumerate(pkeys) if k not in wmap],
            'witness_only':[i for i,k in enumerate(wkeys) if k not in pmap],
            'comparison_basis':'exact directed kind/stance and source spans; differing segmentation is not declared agreement',
            'proposal_only_status':'uncertain_not_silently_committed',
            'witness_only_status':'retained_direct_source_witness_not_independent_corroboration'}


def process(sample,repeat=0,thinking=True,warrant_mode="roles",model=MODEL):
    typing_fn=select_typing(warrant_mode)
    units=source_units(sample);payload=quote_source_payload(sample,units);config=configuration(units,thinking,model)
    suffix='' if thinking else '-no-thinking'
    proposal=invoke(model,'source_proposal_v2',sample['sample_id'],PROPOSAL_PROMPT,payload,lambda o:annotation_from_quotes(o,units),'ontology-v2-proposal-r6'+suffix,repeat,config)
    # Witness input is the original source ONLY. A reversed/missing proposal cannot
    # bias this stage's directed bindings or suppress a missing central relation.
    witness=invoke(model,'source_witness_v2',sample['sample_id'],WITNESS_PROMPT,payload,lambda o:annotation_from_quotes(o,units),'ontology-v2-witness-r6'+suffix,repeat,config)
    for record in [proposal,witness]:
        if record['status']=='accepted':
            record['output']=annotation_from_quotes(record['output'],units)
    row={k:sample.get(k) for k in ['sample_id','article_id','gold','split']}
    row.update(units=units,source_model=model,pipeline='ontology-v2-directed-source-witness-r6',repeat=repeat,
               stage_status={'proposal':proposal['status'],'witness':witness['status'],'warrant':'not_reached'},
               stage_call_ids={'proposal':proposal['call_id'],'witness':witness['call_id'],'warrant':None},
               proposal_annotation=proposal.get('output'),witness_annotation=witness.get('output'))
    if witness['status']!='accepted':return {**row,'status':'witness_failed','annotation':None,'graph':None,'comparison':None}
    annotation=deepcopy(witness['output'])
    for a in annotation['applications']:a.update(scheme='other',scope_change='na',alternatives='na')
    typing=typing_fn(sample,units,annotation,repeat,thinking,invoke_fn=invoke)
    row['stage_status']['warrant']=typing['status'];row['stage_call_ids']['warrant']=typing['call_id'];row['warrant_annotation']=typing.get('output')
    if typing['status'] in ['accepted','not_applicable']:annotation=apply_typing(annotation,typing['output'])
    graph=compile_graph(annotation,units)
    comparison=compare_annotations(proposal.get('output') if proposal['status']=='accepted' else None,annotation,units)
    confirmed={r['witness_index'] for r in comparison['confirmed']}
    for node in graph['nodes']:
        if node['type'] in ['InferenceApplication','ConflictApplication','PreferenceApplication','DiscourseApplication','ReferenceApplication']:
            node['source_verification']='independent_direction_agreement' if node['index'] in confirmed else 'source_witness_only'
            node['source_witness_call_id']=witness['call_id']
    return {**row,'status':'accepted' if typing['status'] in ['accepted','not_applicable'] else 'typing_failed','annotation':annotation,'graph':graph,'comparison':comparison}


def source_failure_guard(rows,window=32,min_valid_rate=.8):
    if len(rows)<window:return None
    recent=rows[-window:];valid=sum(r.get('status')=='accepted' for r in recent)
    if valid/len(recent)<min_valid_rate:return 'source contract validity below '+str(min_valid_rate)+' in last '+str(window)+' completed samples'
    return None


def run_source(samples,name,repeat=0,thinking=True,workers=2,source_mode="joint",warrant_mode="roles",source_model=MODEL,source_examples=False):
    if source_examples and source_mode!="decomposed":raise ValueError("source examples require decomposed mode")
    source_options=dict(warrant_mode=warrant_mode,model=source_model)
    if source_mode=="decomposed":
        source_options["fewshot"]=source_examples
        from decomposed_source_v2 import process as source_process
    elif source_mode=="faceted":
        from faceted_source_v2 import process as source_process
    elif source_mode=="joint":source_process=process
    else:raise ValueError("unknown source mode")
    stop_state={'reason':None}
    def stop_when(rows):
        stop_state['reason']=source_failure_guard(rows)
        return stop_state['reason']
    def save(rows,complete=False):
        metrics={'complete':complete,'expected':len(samples),'completed':len(rows),'graph_contract_valid':sum(r['status']=='accepted' for r in rows),
                 'source_stage_contracts':{stage:{'expected':len(samples),'completed':len(rows),'valid':sum(r['stage_status'][stage] in ['accepted','not_applicable'] for r in rows),'not_reached':sum(r['stage_status'][stage]=='not_reached' for r in rows)} for stage in ['proposal','witness','warrant']},
                 'semantic_acceptance':'measured separately from exact source references; source agreement is not an oracle'}
        metrics['stopped_early']=bool(stop_state['reason']);metrics['stop_reason']=stop_state['reason']
        call_ids={c for row in rows for c in row.get('stage_call_ids',{}).values() if c}
        records={cid:json.loads((ROOT/'calls'/(cid+'.json')).read_text(encoding='utf-8')) for cid in call_ids if (ROOT/'calls'/(cid+'.json')).exists()}
        metrics['stage_contract_attempts']=stage_contract_metrics(rows,records,expected=len(samples))
        (ROOT/(name+'_graphs.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/(name+'_metrics.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
        return metrics
    def extract_row(s):
        row=source_process(s,repeat,thinking,**source_options)
        if source_mode=='faceted':
            from semantic_review_v2 import review_row
            row=review_row(row,s,repeat)
        return row
    rows=batch(samples,extract_row,'Ontology V2 source graphs',workers=workers,on_progress=save,stop_when=stop_when)
    metrics=save(rows,len(rows)==len(samples));ids={c for r in rows for c in r['stage_call_ids'].values() if c}
    render_report(ROOT/(name+'_report.html'),rows,metrics,ids)
    return rows,metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-examples',action='store_true');p.add_argument('--source-model',default=MODEL);p.add_argument('--warrant-mode',choices=['roles','slots'],default='roles');p.add_argument('--source-mode',choices=['joint','decomposed','faceted'],default='joint');p.add_argument('--manifest');p.add_argument('--samples',nargs='*');p.add_argument('--repeat',type=int,default=0);p.add_argument('--name');p.add_argument('--no-thinking',action='store_true');p.add_argument('--interval',type=float,default=12);p.add_argument('--induction',type=int);p.add_argument('--workers',type=int,default=2);p.add_argument('--limit',type=int);args=p.parse_args()
    if args.interval<=0:raise ValueError('positive interval required')
    os.environ['GRAPH_API_INTERVAL']=str(args.interval)
    if args.manifest:
        data=json.loads((ROOT/args.manifest).read_text(encoding='utf-8'));samples=data['samples']
        # Manifests may store original text under source; gold is sampling metadata.
        samples=[{**s,**s.get('source',{}),'gold':s.get('gold',s.get('sampling_label'))} for s in samples]
    else:
        samples=dataset(40)['induction']
        if args.samples:samples=[s for s in samples if s['sample_id'] in args.samples]
        elif args.induction is not None:samples=dataset(args.induction)['induction']
        else:raise ValueError('choose a manifest, explicit samples, or induction count')
    if args.samples:samples=[s for s in samples if s['sample_id'] in args.samples]
    if args.limit is not None:
        if args.limit<=0:raise ValueError('limit must be positive')
        samples=samples[:args.limit]
    if not samples:raise ValueError('no source samples selected')
    name=args.name or 'ontology_v2_source_r'+str(args.repeat)
    rows,metrics=run_source(samples,name,args.repeat,not args.no_thinking,args.workers,args.source_mode,args.warrant_mode,args.source_model,args.source_examples)
    print(json.dumps(metrics,indent=2),flush=True)
    if metrics.get('stopped_early'):raise SystemExit(2)


if __name__=='__main__':main()
