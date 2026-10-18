import argparse
import collections
import json
from pathlib import Path
from core import ROOT,EXTRACT_PROMPT,batch,extract,render_report

MODELS=['meta/llama-3.2-11b-vision-instruct','nvidia/llama-3.1-nemotron-70b-instruct','nvidia/nemotron-3-super-120b-a12b','mistralai/mistral-large-2-instruct']


def controls():
    cases=[
      ('The director says this claim is true. Therefore we should accept this claim.','testimony','uses','normative','na','na'),
      ('Most residents believe the claim. Therefore the claim must be true.','consensus','uses','certain','na','na'),
      ('This method has been used for centuries. Therefore we should keep using this method.','historical_practice','uses','normative','na','na'),
      ('This remedy is completely natural. Therefore the remedy is safe.','natural_property','uses','certain','na','na'),
      ('The local pollution is harmful. Hunger elsewhere is far worse. Therefore we should stop worrying about the local pollution.','priority_comparison','uses','normative','na','na'),
      ('We have only two choices: approve this policy or lose every job. Therefore we must approve this policy.','alternatives','uses','normative','na','closed'),
      ('One member of that group lied to me. Therefore all members of that group are dishonest.','generalization','uses','certain','broader','na'),
      ('If we approve this policy, surveillance will expand. Expanded surveillance will eliminate privacy. Therefore we should reject the policy.','causal_projection','uses','normative','na','na'),
      ('The director says this claim is true. That does not make the claim true.','testimony','critiques','certain','na','na'),
      ('Most residents believe the claim. That does not make the claim true.','consensus','critiques','certain','na','na'),
      ('This method has been used for centuries. That alone is no reason to keep using it.','historical_practice','critiques','normative','na','na'),
      ('This remedy is completely natural. That does not make the remedy safe.','natural_property','critiques','certain','na','na'),
      ('Hunger elsewhere is far worse than local pollution. That does not mean we should stop addressing local pollution.','priority_comparison','critiques','normative','na','na'),
      ('Some people claim our only choices are approving the policy or losing every job. Those are not our only choices. We can negotiate a third option.','alternatives','critiques','certain','na','denied'),
      ('One member of that group lied to me. That does not establish that all members of the group are dishonest.','generalization','critiques','certain','broader','na'),
      ('Some claim approving the policy will expand surveillance and then eliminate privacy. That predicted chain is unsupported.','causal_projection','critiques','certain','na','na'),
      ('The certified laboratory reports that the water contains lead. Therefore we should treat the water as contaminated while checking the report.','testimony','uses','normative','na','na'),
      ('Most voters selected option A in the binding referendum. Therefore option A should be implemented under the agreed voting rule.','consensus','uses','normative','na','na'),
      ('This procedure has worked reliably for decades in the same conditions. Therefore continuing it seems reasonable while monitoring new evidence.','historical_practice','uses','probable','na','na'),
      ('Water naturally expands when it freezes. Therefore a sealed full bottle may crack when frozen.','natural_property','uses','possible','na','na'),
      ('The hospital can fund only one project this month. Preventing immediate deaths is more urgent than repainting the lobby. Therefore the hospital should fund emergency care first.','priority_comparison','uses','normative','na','na'),
      ('This switch has exactly two physical positions, on and off. The switch is not on. Therefore it is off.','alternatives','uses','certain','na','closed'),
      ('A representative random survey found that 60 percent favor the policy. Therefore roughly 60 percent of the population probably favors the policy.','generalization','uses','probable','broader','na'),
      ('If this fuse blows, the circuit will open. An open circuit stops current flow. Therefore the motor will stop if the fuse blows.','causal_projection','uses','certain','na','na'),
      ('The minister argues that most citizens believe the claim. The minister therefore concludes the claim is true. I am only describing that argument, not endorsing it.','consensus','reports','certain','na','na'),
      ('This system failed at one task. Therefore it might fail at similar tasks.','generalization','uses','possible','broader','na'),
      ('The expert says the treatment might help. Therefore the treatment might be worth trying.','testimony','uses','possible','na','na'),
      ('One option is to accept the policy. Another is to reject it. Other options remain available. We should explore additional options.','alternatives','uses','normative','na','open')]
    result=[]
    for i,(text,operator,stance,commitment,scope,alts) in enumerate(cases):
        result.append({'sample_id':'control'+str(i).zfill(2),'comment':text,'title':'','parent_comment':'','expected':{'operator':operator,'stance':stance,'commitment':commitment,'scope_change':scope,'alternatives':alts}})
    return result


def score(output,expected):
    if output['status']!='accepted':return {'full':False,'operator_stance':False,'fields':{k:False for k in expected}}
    args=output['extraction']['arguments']
    best=max(args,key=lambda a:sum(a[k]==v for k,v in expected.items()),default={})
    fields={k:best.get(k)==v for k,v in expected.items()}
    return {'full':all(fields.values()),'operator_stance':fields['operator'] and fields['stance'],'fields':fields}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');ap.add_argument('--models',nargs='+',default=MODELS);ap.add_argument('--version',default='v2');ap.add_argument('--thinking',action='store_true');ap.add_argument('--budget',type=int,default=1024);args=ap.parse_args()
    samples=controls()
    prompt=EXTRACT_PROMPT
    if args.version=='v3':
        from refinements import PROMPT_V3
        prompt=PROMPT_V3
        # Correct reference annotation errors identified against the stated ontology,
        # rather than treating ordinary physical causality as a value-from-nature warrant.
        for s in samples:
            if s['sample_id'] in ['control10','control12']:s['expected']['commitment']='certain'
            if s['sample_id']=='control19':s['expected']['operator']='causal_projection'
    if not args.full:samples=[s for i,s in enumerate(samples) if i in [0,1,5,6,9,10,13,26]]
    jobs=[(model,s) for model in args.models for s in samples]
    def run(job):
        model,s=job
        settings=None
        if args.thinking:
            from core import model_settings
            settings=model_settings(model);settings.update(max_tokens=8192,chat_template_kwargs={'enable_thinking':True,'reasoning_budget':args.budget})
        out=extract(model,s,args.version+'-compact',prompt=prompt,settings=settings);out['control_score']=score(out,s['expected']);return out
    results=batch(jobs,run,'Model/contract screen')
    summary={}
    for model in args.models:
        rows=[r for r in results if r['model']==model]
        summary[model]={'total':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'operator_stance_correct':sum(r['control_score']['operator_stance'] for r in rows),'all_semantic_fields_correct':sum(r['control_score']['full'] for r in rows),'errors':[{k:r[k] for k in ['sample_id','status','extraction','control_score']} for r in rows if not r['control_score']['full']]}
    suffix=('full' if args.full else 'smoke')+('' if args.version=='v2' else '_'+args.version)+('_thinking' if args.thinking else '')+('_b'+str(args.budget) if args.budget!=1024 else '')
    (ROOT/('screen_'+suffix+'.json')).write_text(json.dumps({'controls':samples,'results':results,'summary':summary},ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/'report.html',results,summary)
    print(json.dumps({m:{k:v for k,v in x.items() if k!='errors'} for m,x in summary.items()},indent=2),flush=True)


if __name__=='__main__':main()
