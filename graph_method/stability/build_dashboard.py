"""Rebuild a compact local entry point without making API calls."""
import html
import json
from datetime import datetime,timezone
from core import ROOT


def main():
    escape=html.escape
    parts=['<!doctype html><meta charset="utf-8"><title>Graph experiment evidence</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#172237}pre{white-space:pre-wrap;background:#f1f4f8;padding:15px}details{padding:12px;border:1px solid #ddd;margin:10px}li{margin:8px}</style>',
           '<h1>Graph pipeline: experiment evidence</h1>',
           '<p>Updated '+datetime.now(timezone.utc).isoformat()+'</p>',
           '<p>Stability is not established. Revision 12 passes 28/28 synthetic semantic controls but failed real-source audit; its bulk run stopped after 88 saved graphs. Schema, reasoning-budget and staged-extraction ablations are retained, including their failures. Baseline verification selects the gold label in 39/40 cases where it is retrieved, but overall accuracy is 39/80. Grounded extraction, pattern recovery, repeatability and fresh validation remain required.</p>',
           '<ul><li><a href="ONTOLOGY.md">Ontology</a></li><li><a href="PLAN.md">Fixed acceptance gates</a></li><li><a href="JOURNAL.md">Experiment journal</a></li><li><a href="report.html">Original LLM outputs, prompts, repairs and compiled outputs</a></li><li><a href="manual_audit_v10.json">Real-source diagnostic audit of nested warrants</a></li></ul>',
           '<h2>Research and paper-inspired trials</h2><ul><li><a href="PAPER_SURVEY.md">Survey of original papers and proposed adaptations</a></li><li><a href="ONTOLOGY_V2_DESIGN.md">Ontology revision design: assertions, warrants, conflicts and events</a></li><li><a href="paper_trial_audit.json">Source audit of draft and few-shot trials</a></li></ul>',
           '<h2>Measured results</h2>']
    for path in sorted(ROOT.glob('*metrics.json')):
        value=json.loads(path.read_text(encoding='utf-8'))
        parts.append('<details><summary>'+escape(path.name)+'</summary><pre>'+escape(json.dumps(value,ensure_ascii=False,indent=2))+'</pre></details>')
    for name in ['verify_controls_v4.json','verify_controls_v5.json']:
        path=ROOT/name
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            parts.append('<details><summary>'+escape(name)+'</summary><pre>'+escape(json.dumps(value['metrics'],ensure_ascii=False,indent=2))+'</pre><a href="'+name+'">Every control output</a></details>')
    parts.append('<h2>Outputs by stage</h2><ul>')
    suffixes=('_graphs.json','_patterns.json','_retrieval.json','_evaluations.json')
    for path in sorted(ROOT.glob('*.json')):
        if path.name.endswith(suffixes):parts.append('<li><a href="'+escape(path.name,quote=True)+'">'+escape(path.name)+'</a></li>')
    for path in sorted(ROOT.glob('paper_*_report.html')):
        parts.append('<li><a href="'+escape(path.name,quote=True)+'">'+escape(path.name)+' — prompts, raw outputs and compiled graphs</a></li>')
    for pattern in ['atomic_fidelity*.json','atomic_fidelity*_report.html','guarded*_partial_checks.json','guarded*_report.html','typed_guard*.json','relation_retention*.json','relation_retention_report.html']:
        for path in sorted(ROOT.glob(pattern)):
            parts.append('<li><a href="'+escape(path.name,quote=True)+'">'+escape(path.name)+'</a></li>')
    parts.append('</ul><p>Calls contain complete model inputs, raw outputs, validation outcomes and repairs. Earlier transient infrastructure records are preserved in calls_archive. Test data has not been used for tuning.</p>')
    (ROOT/'index.html').write_text('\n'.join(parts),encoding='utf-8')


if __name__=='__main__':main()
