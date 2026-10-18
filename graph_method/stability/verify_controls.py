import json
from core import ROOT,invoke,batch
from pipeline import MODEL,settings
from unitization import split_units_v5
from screen import controls
from verify import PROMPT,validate_verification,decide

LABELS=['Appeal to Authority','Appeal to Majority','Appeal to Tradition','Appeal to Nature','Appeal to Worse Problems','False Dilemma','Hasty Generalization','Slippery Slope']
OPS=['testimony','consensus','historical_practice','natural_property','priority_comparison','alternatives','generalization','causal_projection']
POSITIVE=[
 'A famous actor with no medical expertise says this drug cures every illness. I have no other evidence. Therefore we should believe the drug cures every illness.',
 'Most people believe the rumor, and I have no evidence beyond its popularity. Therefore the rumor must be true.',
 'This practice is explicitly harmful to people. It has been followed for centuries. Its age alone means we should preserve it.',
 'This poison is natural, even though it can kill people. Its natural origin alone means it is safe to swallow.',
 'Our local pollution harms people and can be addressed without stopping other aid. Hunger elsewhere is worse. Therefore we should ignore the local pollution entirely.',
 'A safe third option exists. Nevertheless I insist our only choices are accepting this dangerous policy or losing every job. Therefore we must accept this policy.',
 'I met exactly one member of the group and that person lied. I have no other examples. Therefore every member of that entire group is dishonest.',
 'Approving one small change will inevitably lead to total surveillance. Total surveillance will inevitably eliminate all freedom. I have no evidence for either step. Therefore we must reject any small change.'
]


def cases():
    source_controls=controls();result=[]
    for i,text in enumerate(POSITIVE):result.append({'sample_id':'verify_positive_'+str(i),'comment':text,'label':LABELS[i],'operator':OPS[i],'reference':'positive'})
    for i in range(8):
        c=source_controls[16+i];result.append({'sample_id':'verify_legitimate_'+str(i),'comment':c['comment'],'label':LABELS[i],'operator':OPS[i],'reference':'legitimate'})
    for i in range(8):
        c=source_controls[8+i];result.append({'sample_id':'verify_critique_'+str(i),'comment':c['comment'],'label':LABELS[i],'operator':OPS[i],'reference':'critique'})
    return result


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--structured',action='store_true');options=parser.parse_args()
    def run(s):
        source={'comment':s['comment'],'title':'','parent_comment':''};units=split_units_v5(source)
        premises=[0]
        if s['sample_id']=='verify_positive_2':premises=[1,2]
        if s['sample_id']=='verify_positive_3':premises=[1]
        if s['sample_id']=='verify_positive_4':premises=[0,1]
        if s['sample_id']=='verify_positive_5':premises=[1]
        if s['sample_id']=='verify_positive_7':premises=[0,1]
        if s['sample_id'] in ['verify_legitimate_4','verify_legitimate_5','verify_legitimate_7']:premises=[0,1]
        arg={'premises':premises,'conclusion':len(units)-1,'operator':s['operator'],'stance':'uses','commitment':'unspecified','scope_change':'broader' if s['operator']=='generalization' else 'na','alternatives':'closed' if s['operator']=='alternatives' else 'na','chain':[]}
        candidate={'id':'c0','label':s['label'],'pattern_id':'control-pattern','constraints':{'operator':s['operator']},'argument_index':0,'mapping':{'premise':'u'+str(premises[0]),'inference':'a0','conclusion':'u'+str(len(units)-1)},'premise_unit_ids':premises,'conclusion_unit_id':len(units)-1,'structural_score':1,'retrieval_score':.8}
        payload={'source':source,'units':units,'extraction':{'arguments':[arg]},'candidates':[candidate]}
        if options.structured:
            from verifier_structured import request,canonicalize
            rec=request(s['sample_id'],payload,version='v5-structured-verify-controls')
            if rec['status']=='accepted':rec={**rec,'output':canonicalize(rec['output'])}
        else:rec=invoke(MODEL,'verify',s['sample_id'],PROMPT,payload,lambda o:validate_verification(o,[candidate],units),'v4-verify-controls',settings=settings())
        decision=decide(rec['output'],[candidate]) if rec['status']=='accepted' else None
        assessment=rec['output']['assessments'][0] if rec['status']=='accepted' else None
        passed=bool(decision) and (decision['selection_status']=='confirmed' if s['reference']=='positive' else decision['selection_status']!='confirmed')
        if s['reference']=='critique':passed=passed and assessment['author']=='challenged'
        return {**s,'status':rec['status'],'passed':passed,'assessment':assessment,'decision':decision}
    results=batch(cases(),run,'Verifier semantic controls')
    metrics={kind:{'count':sum(r['reference']==kind for r in results),'passed':sum(r['reference']==kind and r['passed'] for r in results),'valid':sum(r['reference']==kind and r['status']=='accepted' for r in results)} for kind in ['positive','legitimate','critique']}
    (ROOT/('verify_controls_v5.json' if options.structured else 'verify_controls_v4.json')).write_text(json.dumps({'results':results,'metrics':metrics},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__':main()
