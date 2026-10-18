"""Frozen exposed/fresh audit driver. Never reads test or sends gold labels."""
import argparse
import json
from pathlib import Path
from core import batch,render_report
from pipeline_v2 import run_source
from semantic_review_v2 import review_row,eligible_application
from evaluate_v2 import evaluate_rows,compare_repeats

ROOT=Path(__file__).resolve().parent

def reviewed_rows(rows,samples,name,repeat=0):
    lookup={s['sample_id']:s for s in samples}
    def save(out):
        (ROOT/(name+'_graphs.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    out=batch(rows,lambda r:review_row(r,lookup[r['sample_id']],repeat),name,workers=2,on_progress=save)
    save(out);return out

def selected_rows(rows):
    # Preserve source application indices/targets. Evaluation masks ineligible
    # applications; no silent renumbering or target redirection.
    from copy import deepcopy
    out=deepcopy(rows)
    for row in out:
        if row.get('annotation'):
            for i,a in enumerate(row['annotation']['applications']):
                if not eligible_application(row,i):
                    # Evaluator-only marker, never compiled/mined as a graph.
                    a['kind']='excluded_by_source_review'
    return out

def report(rows,refs,name):
    metrics={'source_audit':evaluate_rows(rows,refs),'selective_audit':evaluate_rows(selected_rows(rows),refs),
             'all_applications':sum(len(r.get('annotation',{}).get('applications',[])) for r in rows if r.get('annotation')),
             'admitted_applications':sum(eligible_application(r,i) for r in rows if r.get('annotation') for i in range(len(r['annotation']['applications']))),
             'warning':'Assistant source references, not expert human gold. Coverage controls are not exhaustive precision.'}
    (ROOT/(name+'_audit.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    ids={c for r in rows for c in r.get('stage_call_ids',{}).values() if c}
    render_report(ROOT/(name+'_report.html'),rows,metrics,ids)
    print(json.dumps({k:v for k,v in metrics.items() if k not in ['source_audit','selective_audit']}),flush=True)
    return metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['critical','fresh','repeat'],required=True);args=p.parse_args()
    if args.phase=='critical':
        samples=json.loads((ROOT/'v2_critical_source_manifest.json').read_text(encoding='utf-8'))['samples']
        rows=json.loads((ROOT/'ontology_v2_faceted_critical_r0_graphs.json').read_text(encoding='utf-8'))
        rows=reviewed_rows(rows,samples,'ontology_v2_faceted_reviewed_critical_r0')
        refs=json.loads((ROOT/'v2_audit_references.json').read_text(encoding='utf-8'))['references'];ids={r['sample_id'] for r in rows}
        report(rows,[r for r in refs if r['sample_id'] in ids],'ontology_v2_faceted_reviewed_critical_r0')
    elif args.phase=='fresh':
        manifest=json.loads((ROOT/'v2_fresh_audit_manifest.json').read_text(encoding='utf-8'))
        samples=[{**s,**s.get('source',{}),'gold':s.get('gold',s.get('sampling_label'))} for s in manifest['samples']]
        rows,_=run_source(samples,'ontology_v2_faceted_fresh_r0',source_mode='faceted',warrant_mode='slots')
        report(rows,manifest['references'],'ontology_v2_faceted_fresh_r0')
    else:
        samples=json.loads((ROOT/'v2_critical_source_manifest.json').read_text(encoding='utf-8'))['samples']
        ids={'469:8603','229:5485','371:6509','524:10868'};samples=[s for s in samples if s['sample_id'] in ids]
        rows,_=run_source(samples,'ontology_v2_faceted_repeat_r1',repeat=1,source_mode='faceted',warrant_mode='slots')
        baseline=json.loads((ROOT/'ontology_v2_faceted_reviewed_critical_r0_graphs.json').read_text(encoding='utf-8'));baseline=[r for r in baseline if r['sample_id'] in ids]
        result=compare_repeats([baseline,rows],[])
        (ROOT/'ontology_v2_faceted_repeat_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result),flush=True)

if __name__=='__main__':main()
