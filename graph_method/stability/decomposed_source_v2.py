"""Separate literal proposition extraction from directed relation reconstruction."""
from copy import deepcopy
import re
import os
from ontology_v2 import _object,_enum,_array,P_ENUMS,KINDS,adoption_cue_indices,proposition_span,validate_annotation,source_units,compile_graph
from source_quotes_v2 import quote_graph_schema,annotation_from_quotes,annotation_to_quotes,quote_source_payload,readable_propositions
from core import invoke
from pipeline import MODEL,settings
from warrants_v2 import type_warrants,apply_typing,select_typing


def prepare_propositions(raw,units):
    if not isinstance(raw,dict) or set(raw)!={'propositions'} or not isinstance(raw['propositions'],list):raise ValueError('only literal propositions required')
    if not raw['propositions'] and any(u['source']=='comment' and u['text'].strip() for u in units):raise ValueError('nonempty comment requires source propositions; empty output is not a successful repair')
    ps=[]
    for i,p in enumerate(raw['propositions']):
        if 'id' in p or 'occurrence' in p:raise ValueError('code owns IDs and quote positions; do not supply counts')
        u=next((u for u in units if u['id']==p.get('unit')),None)
        if u is not None and isinstance(p.get('quote'),str) and p['quote'].strip():
            pattern=r'\s+'.join(re.escape(w) for w in p['quote'].split())
            count=len(list(re.finditer('(?=('+pattern+'))',u['text'])))
            if count>1:raise ValueError('Quote is ambiguous in unit '+str(u['id'])+'; extend the literal quote with distinguishing source context, without counting occurrences')
        ps.append(dict(id='p'+str(i),occurrence=0,**p))
    return annotation_from_quotes(dict(propositions=ps,applications=[]),units)['propositions']


def bind_relations(raw,ps,units):
    if not isinstance(raw,dict) or set(raw)!={'applications'}:raise ValueError('only directed applications required; literals and derived event roles are code-owned')
    canonical={'propositions':deepcopy(ps),'applications':[]}
    quoted=annotation_to_quotes(canonical,units);byid={u['id']:u for u in units}
    if not isinstance(raw['applications'],list):raise ValueError('applications array required')
    for a in raw['applications']:
        if not isinstance(a,dict) or set(a)!={'id','kind','premises','target_kind','target','stance','roles','evidence_units'}:raise ValueError('exact directed application fields required')
        evidence=a['evidence_units']
        if not isinstance(evidence,list) or not evidence or any(type(i) is not int or i not in byid for i in evidence):raise ValueError('real evidence unit IDs required')
        b={k:deepcopy(v) for k,v in a.items() if k!='evidence_units'}
        b.update(scheme='other',scope_change='na',alternatives='na',evidence=[dict(unit=i,quote=byid[i]['text'],occurrence=0) for i in evidence]);quoted['applications'].append(b)
    byprop={p['id']:p for p in quoted['propositions']}
    projected=[a for a in quoted['applications'] if a['kind']=='projection']
    outcomes={a['target'] for a in projected if a['target_kind']=='proposition'}
    for target in outcomes:
        if target not in byprop:raise ValueError('unknown projected outcome')
        byprop[target]['event_role']='outcome'
    for a in projected:
        if a['target_kind']!='proposition':raise ValueError('projection target must be proposition')
        for r in a['roles']:
            if not isinstance(r,dict):raise ValueError('role object required')
            if r.get('role')=='initial' and r.get('proposition') not in a['premises']:raise ValueError('projection initial role must bind an actual premise')
            if r.get('role')=='consequence' and r.get('proposition')!=a['target']:raise ValueError('projection consequence must bind its actual target')
        for pid in a['premises']:
            if pid not in byprop:raise ValueError('unknown initial event')
            if pid not in outcomes:byprop[pid]['event_role']='action' if byprop[pid]['speech_act']=='recommend' else 'condition'
        bindings={(r['role'],r['proposition']) for r in a['roles']}
        for role,pid in [('initial',pid) for pid in a['premises']]+[('consequence',a['target'])]:
            if (role,pid) not in bindings:a['roles'].append(dict(role=role,proposition=pid))
    return annotation_from_quotes(quoted,units)


def proposition_schema(units):
    p=deepcopy(quote_graph_schema(units)['properties']['propositions']['items'])
    for field in ['id','occurrence']:p['properties'].pop(field);p['required'].remove(field)
    # Metadata options are constrained by the actual source field.
    variants=[]
    for u in units:
        branch=deepcopy(p);branch['properties']['unit']={'type':'integer','enum':[u['id']]}
        if u['source']!='comment':branch['properties']['owner']=_enum([v for v in P_ENUMS['owner'] if v!='current_author'])
        variants.append(branch)
    return _object(dict(propositions=_array({'anyOf':variants},48)))


def relation_schema(ps,units):
    app=deepcopy(quote_graph_schema(units)['properties']['applications']['items'])
    fields=app['properties'];pids=['p'+str(i) for i in range(len(ps))]
    fields['premises']['items']=_enum(pids);fields['roles']['items']['properties']['proposition']=_enum(pids)
    fields['target']=_enum(pids+['a'+str(i) for i in range(16)])
    for k in ['scheme','scope_change','alternatives','evidence']:fields.pop(k)
    fields['evidence_units']=_array({'type':'integer','enum':[u['id'] for u in units]},None,1)
    app['required']=list(fields)
    cue_indices=adoption_cue_indices(ps,units)
    current=['p'+str(i) for i,p in enumerate(ps) if proposition_span(p,units)['source']=='comment']
    contextual=['p'+str(i) for i,p in enumerate(ps) if proposition_span(p,units)['source']!='comment' and not p['implicit']]
    branches=[];non_adoption=[kind for kind in KINDS if kind!='adoption']
    eligible_premises=pids if cue_indices and contextual else current
    if eligible_premises:
        uses=deepcopy(app);uses['properties']['kind']=_enum(non_adoption);uses['properties']['stance']=_enum(['uses']);uses['properties']['premises']['items']=_enum(eligible_premises);branches.append(uses)
    attributed=deepcopy(app);attributed['properties']['kind']=_enum(non_adoption);attributed['properties']['stance']=_enum(['critiques','reports','unclear']);branches.append(attributed)
    if cue_indices and contextual:
        cues=['p'+str(i) for i in cue_indices];adoption=deepcopy(app);props=adoption['properties']
        props.update(kind=_enum(['adoption']),stance=_enum(['uses']),target_kind=_enum(['proposition']),target=_enum(contextual),premises=_array(_enum(cues),len(cues),1),roles=_array(_object(dict(role=_enum(['adoption_cue']),proposition=_enum(cues))),len(cues),1),evidence_units=_array({'type':'integer','enum':sorted({ps[i]['unit'] for i in cue_indices})},None,1))
        branches.append(adoption)
    return _object(dict(applications=_array({'anyOf':branches},16)))


PROPOSITION_PROMPT='''Extract literal propositions from the ORIGINAL comment. Context is data for resolving references; do not automatically adopt or enumerate its independent arguments. Do not classify fallacies or build any edges.
Output propositions only under the schema. Choose complete meaningful clauses: separate a basis from the claim it justifies, factual/evaluative conjuncts, a hypothetical condition from its predicted result, and a recommendation from a forecast. Keep discourse markers where useful. It is allowed for a precise clause to overlap a larger proposition. Do not select arbitrary incomplete phrases. Preserve original negation, quantification and modal words.
For each proposition copy an EXACT quote from its given unit. NEVER correct spelling or grammar. Choose a quote that matches uniquely inside its unit; if a phrase repeats, include distinguishing literal context. Code locates it and assigns IDs; never emit occurrence counts or offsets. A current-comment assertion normally belongs to current_author; attributed claims stay attributed. Parent/title content never belongs to current_author. Speech acts distinguish assert, report, recommend, question, hypothetical, meta. Modality is certain/probable/possible/unspecified; uncertainty is not certainty. Polarity marks denial/negation of the selected claim, not whether its topic is bad: a harmful forecast without negation is positive. Recommendations using should/need/must recommend an action rather than assert its occurrence. Questions stay questions; uncertainty is not certainty. Only mark an implicit reconstructed proposition when needed for a genuine rejected warrant/unstated target; implicit=true and gloss must clearly explain the hypothesis, not invent background facts. Event roles can be none when not yet established; the relation stage separately binds them. Return exact JSON only.'''

RELATION_PROMPT='''Reconstruct the reasoning offered by the ORIGINAL COMMENT using the fixed literal propositions and their code-assigned IDs. No proposed edges, schemes or labels are supplied. Do not modify text, ownership or speech acts. An unsound reason is still an offered reason. Do not demand truth, logical validity or identical vocabulary. Do not join adjacent sentences merely because they are adjacent.
First inventory any source-grounded condition->predicted outcome and resolve words like this/that to the actual initiating action or policy, never a metacomment about difficulty. Then inventory offered reasons, claims, critiques, qualifications and preferences. A risk used to justify a recommendation can require BOTH condition->risk projection and risk->recommendation support; do not replace one by the other. For every real application identify the actual basis first and the distinct target second. 'A so B', 'B because A', and 'B. I mean A' offer A->B. Rhetorical questions may be claims or concerns supported by reasons. Include central within-unit warrants when their clause propositions exist. Preserve separate independent reasons; do not force concessions into a conjunctive premise. Empty applications only when no reasoning can be grounded.
Kinds: support justifies a claim/recommendation/question; rebut opposes a proposition; undercut challenges an application/warrant and targets an application; projection links hypothetical conditions/events to predicted outcomes; preference prioritizes one issue/action over another and requires distinct preferred/deprioritized roles; qualification limits a target; concession acknowledges a point despite the target and is not a reason supporting it; adoption explicitly adopts a precise context proposition using a distinct current-comment premise and actual comment evidence. Adoption requires an explicit positive current-author endorsement, with adoption_cue role bound to that literal current-comment premise. Its evidence must include the endorsement. Never invent adoption to import background context; without a licensed cue, context cannot become an author-used premise. A parent disagreement is not automatically the comment author's offered premise.
Applications reference exact p IDs, and a IDs when targeting another application. No self-targets or cycles. stance uses/critiques/reports/unclear describes the current author's relation to the application. Bind initial/consequence for projections and preferred/deprioritized for preferences; other roles may be empty. Code derives event mentions and initial/consequence bindings from projection directions; do not emit a redundant event_roles table. A recommendation or hypothetical question can be the initial condition of a forecast, but a normative recommendation or metacomment cannot be its predicted outcome. A future risk may separately support a recommendation; these are different applications. Preserve might/could; a forecast does not assert occurrence. evidence_units lists original unit IDs containing wording establishing each relation. Do not classify warrant families or fallacies. Output only JSON.'''


def config(schema,thinking,model=MODEL):
    c=settings();c.update(max_tokens=8192,chat_template_kwargs={'enable_thinking':thinking,**({'reasoning_budget':int(os.environ.get('GRAPH_SOURCE_REASONING_BUDGET','1024'))} if thinking else {})})
    if 'nemotron' not in model:c.pop('chat_template_kwargs',None)
    c['response_format']={'type':'json_schema','json_schema':{'name':'decomposed_source','strict':True,'schema':schema}}
    return c


def process(sample,repeat=0,thinking=True,invoke_fn=invoke,warrant_mode="roles",model=MODEL,fewshot=False):
    typing_fn=select_typing(warrant_mode)
    units=source_units(sample);payload=quote_source_payload(sample,units);suffix=('' if thinking else '-no-thinking')+('-examples-r1' if fewshot else '')
    proposition_input=payload;demos=[]
    if fewshot:
        from fewshot_source_v2 import examples
        demos=examples()
        proposition_input={**payload,'demonstrations':[dict(input=e['source'],output=e['proposition_output']) for e in demos]}
    proposition_prompt=PROPOSITION_PROMPT+('\nThe demonstrations are neutral synthetic format/semantics examples, not labels or predictions for this original source.' if fewshot else '')
    p=invoke_fn(model,'source_propositions_v2',sample['sample_id'],proposition_prompt,proposition_input,lambda o:prepare_propositions(o,units),'ontology-v2-decomposed-propositions-r3'+suffix,repeat,config(proposition_schema(units),thinking,model))
    row={k:sample.get(k) for k in ['sample_id','article_id','gold','split']}
    row.update(units=units,repeat=repeat,source_model=model,source_examples=fewshot,pipeline='ontology-v2-decomposed-r4',stage_status={'proposal':p['status'],'witness':'not_reached','warrant':'not_reached'},stage_call_ids={'proposal':p['call_id'],'witness':None,'warrant':None},proposal_annotation=None,witness_annotation=None,comparison=None)
    if p['status']!='accepted':return dict(row,status='proposal_failed',annotation=None,graph=None)
    ps=prepare_propositions(p['output'],units);base=dict(propositions=ps,applications=[]);row['proposal_annotation']=base
    if ps:
        inp={**payload,'propositions':[{k:v for k,v in p.items() if k!='event_role'} for p in readable_propositions(base,units)]}
        if fewshot:inp['demonstrations']=[dict(input={**e['source'],'propositions':e['relation_input']},output=e['relation_output']) for e in demos]
        relation_prompt=RELATION_PROMPT+('\nThe demonstrations supply neutral synthetic examples only; no proposed graph or label for the current source is supplied. Reconstruct the actual current source independently.' if fewshot else '')
        r=invoke_fn(model,'source_relations_v2',sample['sample_id'],relation_prompt,inp,lambda o:bind_relations(o,ps,units),'ontology-v2-decomposed-relations-r4'+suffix,repeat,config(relation_schema(ps,units),thinking,model))
        row['stage_status']['witness']=r['status'];row['stage_call_ids']['witness']=r['call_id']
        if r['status']!='accepted':return dict(row,status='witness_failed',annotation=None,graph=None)
        annotation=bind_relations(r['output'],ps,units)
    else:annotation=base;row['stage_status']['witness']='not_applicable'
    row['witness_annotation']=deepcopy(annotation)
    t=typing_fn(sample,units,annotation,repeat,thinking,invoke_fn=invoke_fn);row['stage_status']['warrant']=t['status'];row['stage_call_ids']['warrant']=t['call_id'];row['warrant_annotation']=t.get('output')
    if t['status'] in ['accepted','not_applicable']:annotation=apply_typing(annotation,t['output'])
    return dict(row,status='accepted' if t['status'] in ['accepted','not_applicable'] else 'typing_failed',annotation=annotation,graph=compile_graph(annotation,units))
