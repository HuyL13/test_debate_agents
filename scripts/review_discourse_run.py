"""Review a completed classification run without making API calls."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from src.discourse_classification.analysis import full_selection_metrics, ranking_ablation
from src.discourse_classification.data import load_records
from src.discourse_classification.runner import render_report
from src.io_utils import read_jsonl, write_json
from src.labels import FALLACIES


def inference_fingerprint():
    paths = [p for p in sorted(Path('src/discourse_classification').glob('*.py')) if p.name != 'analysis.py']
    paths += [Path('src/schemas.py'), Path('src/llm/client.py'), Path('src/llm/openai_client.py')]
    return hashlib.sha256(''.join(str(p) + hashlib.sha256(p.read_bytes()).hexdigest() for p in paths).encode()).hexdigest()


def review(folder, baseline=None, frozen_hash=None):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    rows = read_jsonl(folder / 'results.jsonl')
    selected = manifest['sample_ids']
    if len(rows) != len(selected) or {r['sample_id'] for r in rows} != set(selected):
        raise ValueError('Run incomplete or sample IDs differ from manifest')
    reference = {r['sample_id']: r['gold'] for r in load_records(manifest['config']['input'])}
    if any(reference[r['sample_id']] != r['gold'] for r in rows):
        raise ValueError('Gold differs from input; cannot evaluate')
    actual_hash = inference_fingerprint()
    if frozen_hash and actual_hash != frozen_hash:
        raise ValueError('Frozen inference source changed during evaluation')
    full = full_selection_metrics(rows)
    ablation = ranking_ablation(rows)
    counts = Counter(r['status'] for r in rows)
    correct = sum(r['status'] == 'ok' and r['prediction'] == r['gold'] for r in rows)
    wrong = [r for r in rows if r['status'] == 'ok' and r['prediction'] != r['gold']]
    unresolved = [r for r in rows if r['status'] == 'unresolved']
    absent = [r for r in wrong if r['gold'] not in {c['label'] for c in r.get('candidates', [])}]
    completion = [r for r in rows if r.get('role_completion_focus')]
    failed_completion = [r for r in completion if r.get('role_completion_status') == 'failed']
    summary = json.loads((folder / 'metrics.json').read_text(encoding='utf-8'))
    summary.update(full)
    summary['ranking_ablation'] = ablation
    summary['inference_sha256'] = actual_hash
    summary['role_completion_failures'] = len(failed_completion)
    write_json(folder / 'metrics.json', summary)
    render_report(folder, rows, summary)
    baseline_text = 'No matched historical baseline was supplied.'
    if baseline:
        older = read_jsonl(baseline)
        if {r['sample_id']: r['gold'] for r in older} != {r['sample_id']: r['gold'] for r in rows}:
            raise ValueError('Historical baseline selection/gold differs')
        old_metrics = full_selection_metrics(older)
        baseline_text = (f"Historical single-LLM baseline on the same IDs: accuracy {old_metrics['accuracy_all_selected']:.2%}, "
                         f"macro-F1 {old_metrics['macro_f1_all_selected']:.4f}. "
                         'Its saved manifest does not identify the model, so this is a reference, not a controlled comparison.')
    lines = [
        '# Full classification test review', '',
        f"Version: {manifest['version']}. Model: {manifest['effective_model']['name']}. Recovery: disabled.",
        f'Inference source fingerprint: `{actual_hash}`.', '',
        f'Selected: {len(rows)}; correct: {correct}; wrong: {len(wrong)}; unresolved: {counts["unresolved"]}; errors: {counts["error"]}.',
        f"Accuracy across all selected samples: **{full['accuracy_all_selected']:.2%}**.",
        f"Macro-F1 across all selected samples: **{full['macro_f1_all_selected']:.4f}**.",
        f"Resolved coverage: {counts['ok']/len(rows):.2%}. Unresolved/error samples count as false negatives; they are not a ninth gold label.", '',
        '| Label | Support | Precision | Recall | F1 |',
        '|---|---:|---:|---:|---:|',
    ]
    for label in FALLACIES:
        v = full['per_class_all_selected'][label]
        lines.append(f"| {label} | {v['support']} | {v['precision']:.3f} | {v['recall']:.3f} | {v['f1']:.3f} |")
    lines += ['', baseline_text, '',
        '## Failure decomposition', '',
        f'{len(absent)}/{len(wrong)} wrong predictions lack a gold-label candidate; {len(wrong)-len(absent)} have it but select another label.',
        f'{sum(not r.get("role_arguments") for r in unresolved)}/{len(unresolved)} unresolved rows contain no extracted arguments.',
        f'{sum(bool(r.get("candidates")) for r in unresolved)}/{len(unresolved)} unresolved rows have competing matched candidates.',
        f'{len(completion)}/{len(rows)} rows requested optional role completion; {len(failed_completion)} completions failed.',
        f"Recorded logical request attempts: {sum(r.get('calls', 0) for r in rows)}; provider retries are not included in that count.",
        '', 'Largest failure directions:', '',
    ]
    lines += [f'- {key}: {count}' for key, count in list(full['confusions'].items())[:12]]
    lines += ['', '## Graph contribution check', '',
        f"Removing relations from code ranking changes {ablation['changed_predictions']}/{len(rows)} predictions. "
        f"The replay accuracy is {ablation['accuracy_all_selected']:.2%}, macro-F1 {ablation['macro_f1_all_selected']:.4f}.",
        'This replay holds extracted roles and completion outcomes fixed. It measures ranking sensitivity only; it cannot establish the graph effect on LLM extraction or coverage auditing. No causal graph-improvement claim is justified from this check alone.',
        '', '## Evaluation limits', '',
        'All original test gold labels, including diagnostic sample 599:7794, are preserved and scored. Four test samples were previously used for debugging, so this is not a completely blind held-out evaluation. No classifier, prompt, schema or demonstrations were tuned during this full run.',
        'The HTML report contains every sample and its evidence, candidate structures and graph. Inspect semantic role assignments as well as label matches: an exact quote proves location, not that the assigned basis or inference type is correct.',
    ]
    (folder / 'evaluation.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"Reviewed {len(rows)} rows: accuracy={full['accuracy_all_selected']:.4f}, macro-F1={full['macro_f1_all_selected']:.4f}; evaluation.md")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True)
    ap.add_argument('--baseline')
    ap.add_argument('--frozen-hash')
    args = ap.parse_args()
    review(args.run, args.baseline, args.frozen_hash)


if __name__ == '__main__':
    main()
