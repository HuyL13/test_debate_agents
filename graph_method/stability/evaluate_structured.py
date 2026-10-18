"""Run every retrieved real-source candidate through the constrained verifier."""
import argparse
import json
from core import ROOT,batch,render_report
from pipeline import dataset
from verifier_structured import request,canonicalize
from verify import decide,metrics


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='v3');parser.add_argument('--induction',type=int,default=20);parser.add_argument('--workers',type=int,default=2);parser.add_argument('--snapshot',action='store_true');args=parser.parse_args()
    name='pipeline_'+args.version
    graphs=json.loads((ROOT/(name+'_graphs.json')).read_text(encoding='utf-8'))
    retrieved=json.loads((ROOT/(name+'_retrieval.json')).read_text(encoding='utf-8'))
    if any(r['split']!='development' for r in retrieved):raise ValueError('Development-only evaluation; sealed requires explicit freeze workflow')
    sources={s['sample_id']:s for s in dataset(args.induction)['development']};byid={r['sample_id']:r for r in graphs}
    cached={}
    if args.snapshot:
        for path in (ROOT/'calls').glob('*.json'):
            try:record=json.loads(path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:continue
            if record.get('version')=='v5-structured-verify':cached.setdefault(record['sample_id'],[]).append(record)
    def run(item):
        row=byid[item['sample_id']];source=sources[item['sample_id']];candidates=item['candidates']
        base={k:item[k] for k in ['sample_id','gold','split']}
        if not candidates:return {**base,'status':'no_candidate',**decide({'assessments':[]},[])}
        payload={'source':{k:source.get(k,'') for k in ['comment','title','parent_comment']},'units':row['units'],'extraction':row['extraction'],'candidates':candidates}
        if args.snapshot:
            matching=[r for r in cached.get(item['sample_id'],[]) if r['input']==payload]
            if not matching:return {**base,'status':'pending','prediction':None,'selection_status':'pending','scored_candidates':[]}
            rec=next((r for r in matching if r['status']=='accepted'),matching[0])
        else:rec=request(item['sample_id'],payload)
        decision=decide(canonicalize(rec['output']),candidates) if rec['status']=='accepted' else {'prediction':None,'best_candidate_id':None,'selection_status':rec['status'],'scored_candidates':[]}
        return {**base,'status':rec['status'],'verification_call_id':rec['call_id'],**decision}
    if args.snapshot:
        rows=[run(item) for item in retrieved];completed=[r for r in rows if r['status']!='pending']
        report={'complete':len(completed)==len(rows),'expected':len(rows),'completed':len(completed),'metrics_on_completed_only':metrics(completed) if completed else None}
        (ROOT/(name+'_partial_verification.json')).write_text(json.dumps({'report':report,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return
    rows=batch(retrieved,run,'Structured real-candidate verification',workers=args.workers);report=metrics(rows)
    (ROOT/(name+'_structured_evaluations.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_structured_verification_metrics.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/(name+'_verification_report.html'),rows,report)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
