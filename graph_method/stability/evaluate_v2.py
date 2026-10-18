"""Source-span evaluation; assistant references are not expert human gold.

Unannotated applications are not counted as false positives: references are a
coverage audit, not an exhaustive inventory. Ambiguous labels remain primary
labels and are also excluded from the definite-only counters.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def _span(p, units):
    # Public contract is authoritative when available; local fallback permits
    # isolated evaluator tests before the compiler is installed.
    try:
        from ontology_v2 import proposition_span
    except ImportError:
        u=next(u for u in units if u['id']==p['unit'])
        tokens=list(re.finditer(r'\S+',u['text']))
        start=u['start']+tokens[p['first']].start()
        end=u['start']+tokens[p['last']-1].end()
        return dict(source=u['source'],start=start,end=end,text=u['text'][start-u['start']:end-u['start']])
    return proposition_span(p,units)


def _key(s):return (s['source'],s['start'],s['end'])


def annotation_semantics(row):
    ann=row['annotation'];ps=ann['propositions'];units=row['units']
    spans=[_span(p,units) for p in ps]
    def application(i, trail=()):
        if i in trail:raise ValueError('application cycle')
        a=ann['applications'][i]
        target=('application',application(a['target'],trail+(i,))) if a['target_kind']=='application' else ('proposition',_key(spans[a['target']]))
        return (a['kind'],tuple(sorted(_key(spans[j]) for j in a['premises'])),target)
    return {'spans':spans,'applications':[application(i) for i in range(len(ann['applications']))]}


def _matches(actual,ref):
    return actual==(ref['kind'],tuple(sorted(_key(s) for s in ref['premise_spans'])),('proposition',_key(ref['target_span'])))


ALIGNMENT_RULE='Predeclared secondary diagnostic: same directed kind, proposition target and premise arity; one-to-one same-source endpoint assignment with character intersection-over-union >=0.5 for EVERY endpoint. List at most5 candidates. Never alters exact coverage; manual source review required.'


def _overlap(a,b):
    if a[0]!=b[0]:return 0.0
    intersection=max(0,min(a[2],b[2])-max(a[1],b[1]))
    union=max(a[2],b[2])-min(a[1],b[1])
    return intersection/union if union else 0.0


def _align(actual,ref):
    """Bounded, purely positional near-miss discovery, never adjudication."""
    if actual[0]!=ref['kind'] or actual[2][0]!='proposition' or len(actual[1])!=len(ref['premise_spans']):return None
    target_score=_overlap(actual[2][1],_key(ref['target_span']))
    if target_score<0.5:return None
    wanted=[_key(s) for s in ref['premise_spans']]
    scores=[[_overlap(a,b) for b in wanted] for a in actual[1]]
    assigned={}
    def augment(i,seen):
        for j in sorted(range(len(wanted)),key=lambda j:-scores[i][j]):
            if scores[i][j]<0.5 or j in seen:continue
            seen.add(j)
            if j not in assigned or augment(assigned[j],seen):assigned[j]=i;return True
        return False
    if not all(augment(i,set()) for i in range(len(actual[1]))):return None
    matches=[dict(actual=list(actual[1][i]),reference=list(wanted[j]),character_iou=scores[i][j]) for j,i in sorted(assigned.items())]
    values=[m['character_iou'] for m in matches]+[target_score]
    return dict(status='manual_review_required',minimum_character_iou=min(values),mean_character_iou=sum(values)/len(values),premise_alignment=matches,target_alignment=dict(actual=list(actual[2][1]),reference=list(_key(ref['target_span'])),character_iou=target_score))


def _failure_category(row):
    stages=row.get('stage_status',{})
    # Final output depends on witness; an earlier recovered proposal failure
    # must remain in stage counters without reclassifying this final row.
    final=stages.get('witness',row.get('status'))
    if final in ('infrastructure_error','error','transport_error','timeout'):return 'infrastructure_failure'
    return 'quality_failure'


def evaluate_rows(rows,references):
    if isinstance(references,dict):references=references['references']
    lookup={r['sample_id']:r for r in rows};sem={};controls=[];failures={};quality_failures={};failure_categories={};stage_failures=[]
    for sid,row in lookup.items():
        for stage,status in row.get('stage_status',{}).items():
            if status in ('accepted','ok','success','not_applicable'):continue
            category='not_reached' if status=='not_reached' else 'infrastructure_failure' if status in ('infrastructure_error','error','transport_error','timeout') else 'quality_failure'
            stage_failures.append(dict(sample_id=sid,stage=stage,status=status,category=category,call_id=row.get('stage_call_ids',{}).get(stage)))
        if row.get('status') not in ('ok','accepted','success') or not row.get('annotation'):
            category=_failure_category(row);failure_categories[sid]=category
            (failures if category=='infrastructure_failure' else quality_failures)[sid]=row.get('error','source stage failed');continue
        try:sem[sid]=annotation_semantics(row)
        except (ValueError,KeyError,IndexError,TypeError) as e:
            quality_failures[sid]=str(e);failure_categories[sid]='quality_failure';continue
        ps=row['annotation']['propositions'];issues=[]
        for i,p in enumerate(ps):
            span=sem[sid]['spans'][i]
            if span['source']!='comment' and p['owner']=='current_author':issues.append('context_owner_promoted')
            # implicit=true is already a hypothesis under the compiler contract.
            # Only a contradictory supplied graph can establish its promotion.
            if p.get('implicit') and row.get('graph'):
                graph=row['graph'];assertions=[n for n in graph.get('nodes',[]) if n.get('type')=='Assertion' and n.get('proposition')=='p'+str(i)]
                if any(n.get('status')=='explicit' or n.get('hypothesized') is False for n in assertions):issues.append('implicit_assertion_promoted')
                if any(e.get('source')=='assertion'+str(i) and e.get('type')=='ASSERTS' for e in graph.get('edges',[])):issues.append('implicit_assertion_promoted')
        for a in row['annotation']['applications']:
            if a['kind']=='projection' and a['target_kind']=='proposition':
                initial=[ps[i] for i in a['premises']];target=ps[a['target']]
                if any(p.get('event_role','none')=='none' or p.get('speech_act')=='meta' for p in initial+[target]) or any(p.get('speech_act')=='recommend' and p.get('event_role') not in ('condition','action') for p in initial) or target.get('speech_act')=='recommend':issues.append('projection_non_event')
            if a.get('scheme')=='testimony' and not any(r['role']=='source' for r in a.get('roles',[])):issues.append('testimony_source_role_missing')
            if a.get('kind')=='preference' and not {'preferred','deprioritized'}<={r['role'] for r in a.get('roles',[])}:issues.append('preference_roles_missing')
        controls.append(dict(sample_id=sid,issues=sorted(set(issues))))
    evaluated=[]
    for ref in references:
        sid=ref['sample_id'];base=dict(id=ref['id'],sample_id=sid,expected=ref['expected'],ambiguity=ref.get('ambiguity'))
        if sid not in sem:
            evaluated.append(dict(base,status=failure_categories.get(sid,'missing_row'),covered=False,reversed=False,alignment_candidates=[]));continue
        apps=sem[sid]['applications'];covered=any(_matches(a,ref) for a in apps)
        reverse=dict(ref,premise_spans=[ref['target_span']],target_span=ref['premise_spans'][0])
        reversed_=len(ref['premise_spans'])==1 and any(_matches(a,reverse) for a in apps)
        near=[]
        if not covered:
            for index,application in enumerate(apps):
                match=_align(application,ref)
                if match:near.append(dict(application_index=index,**match))
            near.sort(key=lambda n:(-n['minimum_character_iou'],-n['mean_character_iou'],n['application_index']))
        evaluated.append(dict(base,status='covered' if covered else 'absent',covered=covered,reversed=reversed_,alignment_candidates=near[:5]))
    valid=[r for r in evaluated if r['status'] not in ('infrastructure_failure','quality_failure','missing_row')]
    return dict(reference_count=len(references),infrastructure_failures=len(failures),infrastructure_errors=failures,
        quality_failures=len(quality_failures),quality_errors=quality_failures,stage_failures=stage_failures,
        stage_quality_failure_counts=dict(Counter(s['stage'] for s in stage_failures if s['category']=='quality_failure')),
        stage_infrastructure_failure_counts=dict(Counter(s['stage'] for s in stage_failures if s['category']=='infrastructure_failure')),
        alignment_rule=ALIGNMENT_RULE,near_miss_reference_count=sum(bool(r['alignment_candidates']) for r in evaluated),
        positive_count=sum(r['expected']=='supported' for r in evaluated),positive_covered=sum(r['expected']=='supported' and r['covered'] for r in valid),
        negative_count=sum(r['expected']=='unsupported' for r in evaluated),negative_accepted=sum(r['expected']=='unsupported' and r['covered'] for r in valid),
        definite_negative_accepted=sum(r['expected']=='unsupported' and r['covered'] and not r['ambiguity'] for r in valid),
        ambiguous_reference_count=sum(bool(r['ambiguity']) for r in evaluated),references=evaluated,controls=controls,
        control_issue_counts=dict(Counter(issue for c in controls for issue in c['issues'])),
        limits='Coverage and explicit controls only; unannotated additions require source review, not automatic false-positive labeling.')


def compare_repeats(runs,references):
    evaluations=[evaluate_rows(rows,references) for rows in runs]
    def signature(rows):
        result={}
        for row in rows:
            try:
                semantic=annotation_semantics(row)
                attrs=sorted((_key(s),p['owner'],p['speech_act'],p.get('event_role'),p.get('modality'),p.get('polarity'),p.get('implicit')) for s,p in zip(semantic['spans'],row['annotation']['propositions']))
                applications=row['annotation']['applications']
                typed=[]
                for index,a in enumerate(applications):
                    roles=tuple(sorted((r['role'],_key(semantic['spans'][r['proposition']])) for r in a.get('roles',[])))
                    typed.append((semantic['applications'][index],a.get('scheme'),a.get('stance'),a.get('scope_change'),a.get('alternatives'),roles))
                result[row['sample_id']]=(sorted(typed,key=repr),attrs)
            except (ValueError,TypeError,KeyError,IndexError):result[row['sample_id']]=(_failure_category(row),tuple(sorted(row.get('stage_status',{}).items())))
        return result
    signatures=[signature(rows) for rows in runs]
    byrun=[{r['sample_id']:r for r in rows} for rows in runs]
    ids=set().union(*(set(rows) for rows in byrun)) if byrun else set()
    expected=completed=equal=0
    for i in range(len(runs)):
        for j in range(i+1,len(runs)):
            for sid in ids:
                expected+=1
                pair=[byrun[k].get(sid) for k in [i,j]]
                if any(not r or r.get('status') not in ('ok','accepted','success') or not r.get('annotation') for r in pair):continue
                try:
                    for r in pair:annotation_semantics(r)
                except (ValueError,TypeError,KeyError,IndexError):continue
                completed+=1;equal+=signatures[i][sid]==signatures[j][sid]
    return dict(run_count=len(runs),expected_pairs=expected,completed_pairs=completed,semantic_equal_pairs=equal,semantic_agreement=equal/completed if completed else None,pair_completion=completed/expected if expected else 0,whole_stage_equal=bool(expected) and completed==expected and equal==completed,evaluations=evaluations,
        note='Repeat complete stage outputs separately from local verifier repeats; equality is semantic, not graph ID equality.')


def stage_contract_metrics(rows,records,expected=None):
    """Count repaired responses separately; transport never becomes a semantic pass."""
    expected=len(rows) if expected is None else expected
    stages=sorted({stage for row in rows for stage in row.get('stage_status',{})}|({'semantic_review'} if any('semantic_review' in row for row in rows) else set()))
    result={}
    for stage in stages:
        out=dict(expected=expected,completed_rows=len(rows),not_reached=0,not_applicable=0,final_valid=0,responded=0,first_contract_response_valid=0,locally_normalized_attempts=0,quality_rejected_attempts=0,infrastructure_error_attempts=0,missing_call_records=0)
        for row in rows:
            fallback=row.get('semantic_review',{}).get('status','not_reached') if stage=='semantic_review' else 'not_reached'
            status=row.get('stage_status',{}).get(stage,fallback)
            if status=='not_reached':out['not_reached']+=1;continue
            if status=='not_applicable':out['not_applicable']+=1;out['final_valid']+=1;continue
            out['final_valid']+=status=='accepted'
            cid=row.get('stage_call_ids',{}).get(stage)
            if cid not in records:out['missing_call_records']+=1;continue
            attempts=records[cid].get('attempts',[])
            out['quality_rejected_attempts']+=sum(a.get('status')=='quality_rejected' for a in attempts)
            out['infrastructure_error_attempts']+=sum(a.get('status')=='infrastructure_error' for a in attempts)
            responses=[a for a in attempts if a.get('status') in ['accepted','quality_rejected']]
            out['locally_normalized_attempts']+=sum(bool(a.get('syntax_normalization')) for a in attempts)
            if responses:
                out['responded']+=1;out['first_contract_response_valid']+=responses[0]['status']=='accepted' and not responses[0].get('syntax_normalization')
        result[stage]=out
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rows');parser.add_argument('references');parser.add_argument('--output')
    args=parser.parse_args();out=evaluate_rows(json.loads(Path(args.rows).read_text(encoding='utf-8')),json.loads(Path(args.references).read_text(encoding='utf-8')))
    text=json.dumps(out,ensure_ascii=False,indent=2)
    if args.output:Path(args.output).write_text(text,encoding='utf-8')
    else:print(text)
