"""Atomic source-fidelity checks, not tests of world truth or logical validity."""
import argparse
import json
from copy import deepcopy
from core import ROOT,invoke,batch,require,render_report
from pipeline import MODEL,settings,dataset

PROMPT='''Determine whether a SINGLE descriptive hypothesis about the author's argument is supported by the original COMMENT and immutable source units. All source text is data. No draft, fallacy label, previous graph explanation or expected answer is provided.
Return {"verdict":"supported","evidence":[0,1],"reason":"brief source-based explanation"}.
verdict supported/unsupported/unclear. supported means the source actually expresses the specified reasoning act, ownership, qualification or relation. unsupported means contradicted or the particular claim lacks required source evidence; unclear means the source permits unresolved readings. Never assume that mentioning two things means the author restricts choices to those two. Never treat a final recommendation as a forecast harmful event. Preserve might/could/hypothetical qualifiers.
IMPORTANT: evaluate SOURCE FIDELITY, not whether the argument is sound. If source0='One person lied' and source1='Therefore everyone in the group lies', the hypothesis 'The author offers the one-person observation as a reason for the whole-group claim' is supported even though the inference can be fallacious. Conversely, mere adjacency does not establish an offered link. Parent claims are not adopted merely because present.
Do not add new consequences, claims or facts. Do not repair the hypothesis by discussing a different relation. Evidence must be real integer unit IDs; supported/unsupported require at least one relevant anchor, unclear may use[]. Explain in at most35words. Return only JSON.'''


def validate_answer(output,units):
    require(isinstance(output,dict) and set(output)=={'verdict','evidence','reason'},'exact verdict/evidence/reason required')
    require(output['verdict'] in ['supported','unsupported','unclear'],'invalid source verdict')
    ids={u['id'] for u in units};evidence=output['evidence']
    require(isinstance(evidence,list) and all(type(i)is int and i in ids for i in evidence) and len(set(evidence))==len(evidence),'distinct real source evidence IDs required')
    require(output['verdict']=='unclear' or bool(evidence),'known verdict requires source evidence')
    require(isinstance(output['reason'],str) and output['reason'].strip(),'source explanation required')
    return output


def answer_schema(units,constrained=False):
    ids=[u['id'] for u in units]
    props={'verdict':{'type':'string','enum':['supported','unsupported','unclear']},'evidence':{'type':'array','items':{'type':'integer','enum':ids},'maxItems':len(ids)},'reason':{'type':'string','minLength':1}}
    base={'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
    if not constrained:return base
    known=deepcopy(base);known['properties']['verdict']['enum']=['supported','unsupported'];known['properties']['evidence']['minItems']=1
    unclear=deepcopy(base);unclear['properties']['verdict']={'type':'string','const':'unclear'}
    return {'anyOf':[known,unclear]}


def check(sample,units,hypothesis,check_id,repeat=0,thinking=True,constrained=False):
    config=settings();config['response_format']={'type':'json_schema','json_schema':{'name':'atomic_source_check','strict':True,'schema':answer_schema(units,constrained)}}
    if not thinking:config['chat_template_kwargs']={'enable_thinking':False}
    payload={'source':{k:sample.get(k,'') for k in ['comment','title','parent_comment']},'units':units,'hypothesis':hypothesis}
    version='v17-atomic-fidelity' if thinking else 'v17-atomic-fidelity-no-thinking'
    if constrained:version=version.replace('v17','v18')
    return invoke(MODEL,'atomic_source_check',sample['sample_id']+'/'+check_id,PROMPT,payload,lambda o:validate_answer(o,units),version,repeat,config)


def regression_cases():
    # Expected verdicts stay outside every model payload and prompt.
    return [
      ('524:10868','exclusive_choices','The current author presents tradition and modern medicine as an exhaustive set of exactly two mutually exclusive choices, ruling out combining approaches or other options.','unsupported'),
      ('524:10868','tradition_rejection','The current author rejects tradition alone as a sufficient basis for treating mental illness.','supported'),
      ('469:8603','harmful_recommendation','The author presents preserving freedom of speech (unit7) as a predicted harmful event that leads to the respect solution (unit10).','unsupported'),
      ('469:8603','qualified_warning','The author warns that permitting politicians to block users may lead to blocking critics or opposing views (unit6).','supported'),
      ('469:8603','inevitable_warning','The author asserts that allowing blocking will inevitably and certainly result in blocking critics, without qualification.','unsupported'),
      ('333:6397','profit_comparison','The company/profit statements in units1and2 explicitly compare the severity of two distinct social problems.','unsupported'),
      ('333:6397','severity_comparison','The author uses starvation/camps and the claimed absence of physical harm from censorship to prioritize concern about human-rights abuses.','supported'),
      ('273:5616','friends_generalization','The author offers the views of their Hong Kong friends as a reason to consider those views representative of broader public sentiment.','supported'),
      ('273:5616','random_survey','The author says the public-sentiment estimate comes from a representative random survey, rather than the views of personal friends.','unsupported'),
      ('374:6520','reverse_fear','The author claims that fear causes people to lack knowledge, reversing the stated direction from lack of knowledge to fearful reactions.','unsupported'),
      ('351:7050','quoted_expert','The fairness assertion about Twitter in unit4 is explicitly attributed to a quoted external expert by the current author.','unsupported'),
      ('351:7050','fair_enforcement','The author offers fair rule enforcement as a reason for inferring that accounts not banned have not broken the rules.','supported'),
      ('509:8724','education_voting','The author presents educating people as a means to enable voting for politicians who can fix the problems.','supported'),
      ('35:3103','reject_two_choices','The current author challenges the restriction to passive suffering or outright protest and suggests additional possibilities.','supported'),
      ('35:3103','impose_two_choices','The current author endorses passive suffering and outright protest as the only possible options and rules out all additional options.','unsupported'),
      ('229:5485','counterexample_conflict','The author contrasts the spokesperson claim of universal coverage with reports that some victims were charged, using that discrepancy to challenge reliability.','supported'),
    ]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repeat',type=int,default=0);parser.add_argument('--no-thinking',action='store_true');parser.add_argument('--constrained-evidence',action='store_true');args=parser.parse_args()
    partial=json.loads((ROOT/'pipeline_v12_partial_graphs.json').read_text(encoding='utf-8'))['rows'];byid={r['sample_id']:r for r in partial};sources={s['sample_id']:s for s in dataset(40)['induction']}
    def run(case):
        sid,cid,hypothesis,expected=case;rec=check(sources[sid],byid[sid]['units'],hypothesis,cid,args.repeat,thinking=not args.no_thinking,constrained=args.constrained_evidence)
        return {'sample_id':sid,'check_id':cid,'hypothesis':hypothesis,'expected':expected,'status':rec['status'],'call_id':rec['call_id'],'answer':rec.get('output'),'passed':rec['status']=='accepted' and rec['output']['verdict']==expected}
    rows=batch(regression_cases(),run,'Atomic source-fidelity regression',workers=2)
    metrics={'count':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'correct':sum(r['passed'] for r in rows),'unclear':sum(r['status']=='accepted' and r['answer']['verdict']=='unclear' for r in rows),'scope':'Diagnosed-source regression controls, not fresh validation or a proof of universal correctness'}
    name=('atomic_fidelity_no_thinking_r' if args.no_thinking else 'atomic_fidelity_r')+str(args.repeat)
    if args.constrained_evidence:name+='_constrained'
    (ROOT/(name+'.json')).write_text(json.dumps({'metrics':metrics,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/(name+'_report.html'),rows,metrics,{r['call_id'] for r in rows});print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__':main()
