"""Render terminal experimental evidence without relabeling validity as accuracy."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name):
    p=ROOT/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

def main():
    critical=load('ontology_v2_faceted_critical_r0_metrics.json')
    fresh=load('ontology_v2_faceted_fresh_r0_metrics.json')
    fresh_audit=load('ontology_v2_faceted_fresh_r0_audit.json')
    reviewed=load('ontology_v2_faceted_reviewed_critical_r0_audit.json')
    repeat=load('ontology_v2_source_review_repeat_audit.json')
    pair=load('ontology_v2_pair_diagnostic_r0_graphs.json')
    result=dict(decision='reviewed_train_graph_supervision_with_selective_matching',
                automatic_prompt_only_induction='rejected',
                semantic_accuracy_estimate=None,
                semantic_accuracy_note='No exhaustive expert-gold precision audit. Contract, reference coverage and repeat agreement are separate metrics.',
                final_pattern_bank_ready=False,
                readiness_note='No expert-reviewed training bank has been produced; no eight-label support/held-out usefulness gate is claimed.',
                critical_contract=critical,
                critical_source_review=reviewed,
                reserved_train_contract=fresh,
                reserved_train_source_audit=fresh_audit,
                fixed_graph_reviewer_repeat=repeat,
                pair_diagnostic=dict(samples=len(pair),completed=sum(r['status']=='accepted' for r in pair)) if pair else None)
    (ROOT/'FINAL_EXPERIMENT_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    links=[('FINAL_METHOD_DECISION.md','Selected method, risk treatment and implementation limits'),('FINAL_SOURCE_AUDIT_NOTES.md','Source-reviewed failures and evaluation limits'),('RELATION_ANNOTATION_GUIDE.md','Training graph annotation protocol'),('FINAL_AUDIT_INTEGRITY.json','Frozen source files and article-disjoint audit'),('ontology_v2_faceted_reviewed_critical_r0_report.html','Nine difficult TRAIN cases: graph outputs and source reviews'),('ontology_v2_faceted_fresh_r0_report.html','Sixteen reserved TRAIN cases: every stage and raw responses'),('ontology_v2_pair_diagnostic_r0_report.html','Fixed-endpoint pair diagnostic, including failures'),('ontology_v2_source_review_repeat_audit.json','Repeated source review: agreements and disagreements'),('FINAL_EXPERIMENT_RESULTS.json','Machine-readable final evidence'),('PAPER_SURVEY.md','Primary research and adaptations')]
    parts=['<!doctype html><meta charset="utf-8"><title>Final graph method decision</title><style>body{font:16px system-ui;max-width:1100px;margin:36px auto;padding:18px;color:#172237}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f8;padding:16px}li{margin:12px}</style>',
           '<h1>Final method decision</h1><p><strong>Use reviewed TRAIN graph supervision and selective matching. Prompt-only automatic pattern induction is rejected by the source diagnostics.</strong></p><p>The method is selected; the original automatic stability and eight-label usefulness gates have not passed. No expert-gold semantic accuracy percentage is claimed.</p><ul>']
    parts.extend('<li><a href="'+path+'">'+html.escape(label)+'</a></li>' for path,label in links if (ROOT/path).exists())
    parts.extend(['</ul><h2>Evidence</h2><pre>',html.escape(json.dumps(result,ensure_ascii=False,indent=2)),'</pre>'])
    (ROOT/'FINAL_METHOD_REPORT.html').write_text('\n'.join(parts),encoding='utf-8')
    print(json.dumps({'critical_complete':bool(critical and critical.get('complete')),'fresh_complete':bool(fresh and fresh.get('complete')),'review_repeat_complete':bool(repeat and repeat['completed_rows']==repeat['expected_rows']),'automatic_method':'rejected'},indent=2))

if __name__=='__main__':main()
