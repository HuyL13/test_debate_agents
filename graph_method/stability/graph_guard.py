"""Commit proposed graph properties only after atomic source checks.

This is an experimental guard, not a certificate of semantic truth. Unknown
properties remain explicit and candidate coverage must be audited separately.
"""
import argparse
import hashlib
import json
import os
from copy import deepcopy
from core import ROOT,batch,compile_graph,render_report
from pipeline import dataset
from atomic_fidelity import check

SCHEMES={
 'testimony':'The offered warrant relies on an external source\'s attributed statement, endorsement, credibility, expertise or status, rather than merely mentioning an entity or stating the current author\'s own observation.',
 'consensus':'Collective belief, popularity, participation or collective choice is the particular offered or explicitly challenged justification, not merely the subject being people.',
 'historical_practice':'Tradition, longevity or precedent functions as the offered or explicitly challenged justification, not merely a historical description.',
 'natural_property':'Naturalness or normality functions as justification of value, acceptability or action, not merely an ordinary physical cause or descriptive observation.',
 'priority_comparison':'The offered reason compares the importance or severity of issues or actions to prioritize or deprioritize the focal concern, rather than merely describing a company or its profit motive.',
 'alternatives':'An actual set of choices and its restriction or openness functions as the offered or challenged reason. Merely rejecting one action and recommending another does not establish an exhaustive choice set.',
 'generalization':'An observed case, sample or property is extrapolated to a broader unobserved target in this particular link; the previous broader conclusion is not itself the observed sample.',
 'causal_projection':'A stated projected action/process consequence functions as the offered justification or the specific consequence link being challenged, not merely a claim that predicts a group property.',
 'analogy':'An offered similarity between distinct cases is used to transfer a conclusion from one case to the other.',
 'evidence':'The particular mapped factual premises provide offered support or an explicitly challenged basis for this target, rather than merely being adjacent assertions.',
}


def projection_hypothesis(left,right):
    return 'The author presents the action/condition described at unit '+str(left)+' as leading to the projected consequence described at unit '+str(right)+'. The second unit is an outcome in the scenario, not merely a later recommendation, metacomment or expression of disagreement. A proposed initial policy can supply the hypothetical first condition; actual occurrence need not be asserted.'


def hypotheses(row,typed=False):
    result=[]
    for index,arg in enumerate(row['extraction']['arguments']):
        key='a'+str(index);mapping='For the PARTICULAR mapped premises '+str(arg['premises'])+' and target unit '+str(arg['conclusion'])+', '
        stances={'uses':'the current author relies on this reason-to-target link','critiques':'the current author explicitly challenges the sufficiency of this proposed justification in relation to the target discussion','reports':'the current author merely reports this offered link without adopting it','unclear':'the source leaves the current author\'s ownership of this offered link unresolved'}
        binding=mapping+stances[arg['stance']]+'. The source actually offers/evaluates this particular link; it is not inferred merely from adjacency.'
        direct_transition=arg['operator']=='causal_projection' and len(arg['premises'])==1 and arg['chain']==arg['premises']+[arg['conclusion']]
        direct_transition=direct_transition and arg['stance']=='uses'
        if typed and direct_transition:
            binding=projection_hypothesis(arg['premises'][0],arg['conclusion'])
        result.append((key+'_binding',binding))
        if arg['operator'] in SCHEMES:
            text=mapping+SCHEMES[arg['operator']]
            if typed and direct_transition:
                text=projection_hypothesis(arg['premises'][0],arg['conclusion'])
            if arg['operator']=='alternatives':text+=' The source treatment of the choice set is '+arg['alternatives']+'.'
            if arg['operator']=='generalization':text+=' The proposed scope transition is '+arg['scope_change']+'.'
            result.append((key+'_scheme',text))
        descriptions={
          'certain':'the target is presented as an unhedged factual/evaluative assertion or asserted conditional, rather than as a mere question, recommendation or explicitly tentative possibility',
          'probable':'the target is qualified as likely/probable rather than asserted certain or merely prescribed',
          'possible':'the target content is qualified as a tentative possibility, considering the original clause envelope, rather than asserted inevitable or merely prescribed',
          'normative':'the target expresses the current author\'s recommendation or requirement about what should be done, rather than a predicted harmful event',
        }
        if arg['commitment'] in descriptions:result.append((key+'_commitment','At target unit '+str(arg['conclusion'])+', '+descriptions[arg['commitment']]+'.'))
        for pair,(left,right) in enumerate(zip(arg['chain'],arg['chain'][1:])):
            result.append((key+'_chain'+str(pair),projection_hypothesis(left,right)))
    return result


def source_obligations(row,typed=False):
    """One request per identical claim; aliases preserve all graph obligations."""
    grouped={}
    for key,hypothesis in hypotheses(row,typed=typed):grouped.setdefault(hypothesis,[]).append(key)
    return [(next((k for k in keys if '_chain' in k),keys[0]),hypothesis,keys) for hypothesis,keys in grouped.items()]


def supported(answers,key):
    return answers.get(key,{}).get('status')=='accepted' and answers[key].get('verdict')=='supported'


def compile_guarded(row,answers,typed=False):
    arguments=[];provenance=[];uncommitted=[];by_relation={};conflicts=[]
    for index,original in enumerate(row['extraction']['arguments']):
        key='a'+str(index)
        if typed:
            equivalent=[key+'_binding']
            if original['operator']=='evidence':equivalent.append(key+'_scheme')
            if original['operator']=='causal_projection' and original['stance']=='uses' and original['chain']==original['premises']+[original['conclusion']] and len(original['premises'])==1:
                equivalent.extend([key+'_scheme',key+'_chain0'])
            known={qid:answers[qid]['verdict'] for qid in equivalent if answers.get(qid,{}).get('status')=='accepted' and answers[qid].get('verdict') in ['supported','unsupported']}
            if len(set(known.values()))>1:
                conflicts.append({'argument_index':index,'checks':known,'resolution':'quarantined_pending_source_review'})
                uncommitted.append(index);continue
        if not supported(answers,key+'_binding'):
            uncommitted.append(index);continue
        argument=deepcopy(original);uncertain=[]
        if original['operator']=='other' or not supported(answers,key+'_scheme'):
            argument.update(operator='other',scope_change='na',alternatives='na',chain=[])
            if 'escalation' in argument:argument['escalation']='na'
            uncertain.append('scheme')
        if original['commitment']=='unspecified' or not supported(answers,key+'_commitment'):
            argument['commitment']='unspecified';uncertain.append('commitment')
        if original['chain'] and not all(supported(answers,key+'_chain'+str(pair)) for pair in range(len(original['chain'])-1)):
            argument['chain']=[];uncertain.append('projected_chain')
            if 'escalation' in argument and argument['operator']=='causal_projection':argument['escalation']='unclear'
        if argument.get('escalation') not in [None,'na','unclear']:
            argument['escalation']='unclear';uncertain.append('escalation')
        relation=(tuple(sorted(argument['premises'])),argument['conclusion'],argument['operator'],argument['stance'])
        proof_ids={qid:answer.get('call_id') for qid,answer in answers.items() if qid.startswith(key+'_')}
        if relation in by_relation:
            existing=by_relation[relation];origin=provenance[existing];origin['proposal_argument_indices'].append(index);origin['proof_call_ids'].update(proof_ids)
            for field,unknown in [('commitment','unspecified'),('scope_change','unclear'),('alternatives','unclear')]:
                if arguments[existing][field]!=argument[field]:arguments[existing][field]=unknown;uncertain.append(field)
            if arguments[existing]['chain']!=argument['chain']:arguments[existing]['chain']=[];uncertain.append('projected_chain')
            origin['uncertain_properties']=sorted(set(origin['uncertain_properties']+uncertain));continue
        by_relation[relation]=len(arguments)
        arguments.append(argument)
        provenance.append({'proposal_argument_index':index,'proposal_argument_indices':[index],'uncertain_properties':uncertain,'proof_call_ids':proof_ids})
    extraction={'arguments':arguments};graph=compile_graph(extraction,row['units'])
    for node in graph['nodes']:
        if node['kind']=='inference':
            node.update(provenance[int(node['id'][1:])])
            node['verification_status']='source_checked_proposal_not_oracle'
    return {'extraction':extraction,'graph':graph,'argument_provenance':provenance,'uncommitted_argument_indices':uncommitted,'verification_conflicts':conflicts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',default='paper_verified_draft_r0_graphs.json');parser.add_argument('--no-thinking',action='store_true');parser.add_argument('--constrained-evidence',action='store_true');parser.add_argument('--interval',type=float);parser.add_argument('--typed-relations',action='store_true');parser.add_argument('--repeat',type=int,default=0);args=parser.parse_args()
    if args.interval is not None:
        if args.interval<=0:raise ValueError('positive API interval required')
        os.environ['GRAPH_API_INTERVAL']=str(args.interval)
    path=ROOT/args.input;rows=json.loads(path.read_text(encoding='utf-8'));sources={s['sample_id']:s for s in dataset(40)['induction']}
    if any(row.get('status')!='accepted' for row in rows):raise ValueError('Guard only accepted proposal contracts; keep other failures explicit upstream')
    jobs=[];lookup={}
    for row in rows:
        fingerprint=hashlib.sha256(json.dumps({'units':row['units'],'extraction':row['extraction']},sort_keys=True).encode()).hexdigest()[:12]
        lookup[row['sample_id']]=row
        jobs.extend((row['sample_id'],fingerprint,key,hypothesis,aliases) for key,hypothesis,aliases in source_obligations(row,typed=args.typed_relations))
    def run(job):
        sid,fingerprint,key,hypothesis,aliases=job;rec=check(sources[sid],lookup[sid]['units'],hypothesis,'guard-'+fingerprint+'-'+key,repeat=args.repeat,thinking=not args.no_thinking,constrained=args.constrained_evidence)
        return [{'sample_id':sid,'check_key':alias,'canonical_check_key':key,'hypothesis':hypothesis,'status':rec['status'],'call_id':rec['call_id'],**(rec.get('output') or {})} for alias in aliases]
    name='guarded_'+path.stem+('_no_thinking' if args.no_thinking else '')+('_constrained' if args.constrained_evidence else '')
    if args.typed_relations:name+='_typed_v3_r'+str(args.repeat)
    elif args.repeat:name+='_r'+str(args.repeat)
    expected=sum(len(job[-1]) for job in jobs)
    def checkpoint(partial,complete=False):
        checks=[record for group in partial for record in group]
        (ROOT/(name+'_partial_checks.json')).write_text(json.dumps({'complete':complete,'expected':expected,'completed':len(checks),'unique_obligations':len(jobs),'completed_unique_obligations':len(partial),'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    groups=batch(jobs,run,'Atomic graph guard',workers=2,on_progress=checkpoint)
    checks=[record for group in groups for record in group];results=[]
    for row in rows:
        answers={r['check_key']:r for r in checks if r['sample_id']==row['sample_id']}
        results.append({'sample_id':row['sample_id'],'gold':row.get('gold'),'units':row['units'],'proposal_extraction':row['extraction'],'source_checks':answers,'status':'checked_with_explicit_uncertainty',**compile_guarded(row,answers,typed=args.typed_relations)})
    metrics={'count':len(results),'source_checks':len(checks),'check_contract_valid':sum(r['status']=='accepted' for r in checks),'proposed_relations':sum(len(r['extraction']['arguments']) for r in rows),'retained_relations':sum(len(r['extraction']['arguments']) for r in results),'uncommitted_relations':sum(len(r['uncommitted_argument_indices']) for r in results),'warning':'Needs source audit and coverage/repeatability evaluation; verifier agreement is not semantic ground truth.'}
    metrics['verification_conflicts']=sum(len(r['verification_conflicts']) for r in results)
    metrics['unique_source_obligations']=len(jobs)
    metrics['unique_check_contract_valid']=sum(group[0]['status']=='accepted' for group in groups)
    (ROOT/(name+'_graphs.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_metrics.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/(name+'_report.html'),results,metrics,{r['call_id'] for r in checks})
    checkpoint(groups,complete=True)
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__':main()
