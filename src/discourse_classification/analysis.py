"""Post-run analysis only; never imported by the inference path."""
from collections import Counter

from src.labels import FALLACIES


def full_selection_metrics(rows):
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate sample IDs')
    if any(r['gold'] not in FALLACIES for r in rows):
        raise ValueError('Gold outside the classification label space')
    gold = Counter(r['gold'] for r in rows)
    predicted = Counter(r['prediction'] for r in rows if r['status'] == 'ok')
    if any(label not in FALLACIES for label in predicted):
        raise ValueError('Prediction outside the classification label space')
    correct = Counter(r['gold'] for r in rows if r['status'] == 'ok' and r['prediction'] == r['gold'])
    per_class = {}
    for label in FALLACIES:
        tp = correct[label]
        precision = tp / predicted[label] if predicted[label] else 0.
        recall = tp / gold[label] if gold[label] else 0.
        f1 = 2 * tp / (predicted[label] + gold[label]) if predicted[label] + gold[label] else 0.
        per_class[label] = {'support': gold[label], 'precision': precision, 'recall': recall, 'f1': f1}
    confusions = Counter()
    for row in rows:
        outcome = row['prediction'] if row['status'] == 'ok' else row['status'].upper()
        if outcome != row['gold']:
            confusions[f"{row['gold']} -> {outcome}"] += 1
    return {'accuracy_all_selected': sum(correct.values()) / len(rows) if rows else 0.,
            'macro_f1_all_selected': sum(v['f1'] for v in per_class.values()) / len(FALLACIES),
            'per_class_all_selected': per_class, 'confusions': dict(confusions.most_common())}


def ranking_ablation(rows):
    """Hold LLM extractions fixed; remove graph relations from code ranking only.

    This does not measure graph effects on extraction or coverage completion.
    """
    if any(r.get('decision_mode', '').startswith('verified') for r in rows):
        return {'available': False, 'scope': 'Final decisions require an actual verifier rerun without relations; template replay is not a verifier ablation.'}
    from src.discourse_classification.roles import match_arguments, select_candidate
    replay, changed = [], 0
    for row in rows:
        if row['status'] == 'error' or 'graph' not in row:
            replay.append(row)
            continue
        arguments = row.get('role_arguments')
        if arguments is None:
            arguments = [{'kind': c['anchor'], **c['attributes'], 'stance': c['stance'],
                          'relation_status': c['relation_status'], 'evidence': c['evidence']}
                         for c in row.get('candidates', [])]
        graph = {**row['graph'], 'relations': [], 'edges': []}
        candidates = match_arguments(graph, {'comment': row['comment']}, arguments)
        winner = select_candidate(candidates, row.get('role_completion_focus', []))
        prediction = winner['label'] if winner else None
        changed += prediction != row.get('prediction')
        replay.append({**row, 'prediction': prediction, 'status': 'ok' if winner else 'unresolved'})
    return {**full_selection_metrics(replay), 'changed_predictions': changed,
            'scope': 'Code ranking only, holding extracted roles and completion outcomes fixed.'}
