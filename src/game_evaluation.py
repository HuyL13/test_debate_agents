"""Offline outcome utility and proper forecast scoring. Never used as model input."""
from collections import Counter
from pathlib import Path
import json
import math

from src.evaluate import score
from src.io_utils import digest, read_jsonl
from src.labels import FALLACIES


def evaluate_game(rows, *, benefit=1.0, harm=1.0, token_penalty=0.0, total_tokens=0):
    for weight in (benefit, harm, token_penalty):
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
            raise ValueError('Utility weights must be finite nonnegative numbers')
    if type(total_tokens) is not int or total_tokens < 0:
        raise ValueError('total_tokens must be a nonnegative integer')
    final_metrics = score(rows)  # Coverage/errors/duplicates cannot silently disappear.
    if final_metrics['task'] != 'classification':
        raise ValueError('Game evaluation is classification only')
    counts = Counter()
    actions = Counter()
    brier = []; log_losses = []
    for row in rows:
        initial = row['prosecutor']['candidate_class']
        if initial not in FALLACIES:
            raise ValueError('Invalid Prosecutor candidate')
        final, gold = row['prediction'], row['gold']
        counts['beneficial'] += initial != gold and final == gold
        counts['harmful'] += initial == gold and final != gold
        counts['wrong_to_wrong'] += initial != gold and final != gold and final != initial
        counts['unchanged'] += initial == final
        raw = row.get('defender_review', {})
        actions[raw.get('action', raw.get('decision', 'legacy'))] += 1
        arbiter = row.get('arbiter', {})
        game = arbiter.get('game_trace', {})
        if game:
            offered = game['candidate_classes']
            counts['candidate_set_contains_gold'] += gold in offered
            counts['unresolved_verdicts'] += arbiter['resolution'] != 'selected'
        probs = arbiter.get('probabilities')
        if probs is not None:
            if set(probs) != set(FALLACIES) or any(type(p) not in (int, float) or
                not math.isfinite(p) or not 0 <= p <= 1 for p in probs.values()) or not math.isclose(sum(probs.values()), 1.0, abs_tol=1e-6):
                raise ValueError('Invalid unconditional eight-class forecast')
            brier.append(sum((probs[label] - int(label == gold)) ** 2 for label in FALLACIES))
            log_losses.append(-math.log(max(probs[gold], 1e-15)))
    net = counts['beneficial'] - counts['harmful']
    utility = benefit * counts['beneficial'] - harm * counts['harmful'] - token_penalty * total_tokens
    return {'count': len(rows), 'final': final_metrics, 'counts': dict(counts),
            'actions': dict(actions), 'net_corrections': net, 'utility_total': utility,
            'utility_per_sample': utility / len(rows),
            'utility_parameters': {'benefit': benefit, 'harm': harm, 'token_penalty': token_penalty,
                                   'total_tokens': total_tokens},
            'forecast_count': len(brier), 'mean_brier': sum(brier)/len(brier) if brier else None,
            'mean_log_loss': sum(log_losses)/len(log_losses) if log_losses else None,
            'note': 'Offline gold-based evaluation only. Utility is not Macro-F1. Forecasts are not assumed calibrated.'}


def _load_replay(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    if 'snapshot' not in manifest or manifest.get('fingerprint') != digest({k: v for k, v in manifest.items() if k != 'fingerprint'}):
        raise ValueError('Comparison requires a valid exact-replay manifest')
    rows = read_jsonl(directory/'predictions.jsonl')
    ids = [r['sample_id'] for r in rows]
    if not rows or len(ids) != len(set(ids)) or set(ids) != set(manifest['sample_ids']):
        raise ValueError('Replay coverage mismatch')
    if any(r['run_fingerprint'] != manifest['fingerprint'] or r.get('status') != 'ok' for r in rows):
        raise ValueError('Replay incomplete or fingerprint mismatch')
    summary = json.loads((directory/'summary.json').read_text())
    if summary['status'] != 'complete' or summary['snapshot'] != manifest['snapshot']:
        raise ValueError('Replay summary incomplete or snapshot mismatch')
    return manifest, rows, summary


def compare_replays(baseline, candidate, **weights):
    old_manifest, old, old_summary = _load_replay(baseline)
    new_manifest, new, new_summary = _load_replay(candidate)
    if old_manifest['snapshot'] != new_manifest['snapshot']:
        raise ValueError('Paired comparison requires the exact same Prosecutor snapshot')
    a = {r['sample_id']: r for r in old}; b = {r['sample_id']: r for r in new}
    if set(a) != set(b):
        raise ValueError('Paired sample sets differ')
    for sid in a:
        if a[sid]['gold'] != b[sid]['gold'] or a[sid]['prosecutor'] != b[sid]['prosecutor']:
            raise ValueError('Paired gold or exact Prosecutor reports differ')
    results = []
    for rows, summary in ((old, old_summary), (new, new_summary)):
        if weights.get('token_penalty', 0) and summary['usage'].get('missing_usage_responses', 0):
            raise ValueError('Token utility requires complete token usage')
        results.append(evaluate_game(rows, total_tokens=summary['usage']['total_tokens'], **weights))
    gained = sum(a[sid]['prediction'] != a[sid]['gold'] and b[sid]['prediction'] == b[sid]['gold'] for sid in a)
    lost = sum(a[sid]['prediction'] == a[sid]['gold'] and b[sid]['prediction'] != b[sid]['gold'] for sid in a)
    return {'snapshot': old_manifest['snapshot'], 'paired_count': len(a),
            'synthetic': bool(old_summary.get('synthetic') or new_summary.get('synthetic')),
            'baseline': results[0], 'candidate': results[1],
            'paired_gained': gained, 'paired_lost': lost,
            'delta_accuracy': results[1]['final']['accuracy'] - results[0]['final']['accuracy'],
            'delta_macro_f1': results[1]['final']['macro_f1'] - results[0]['final']['macro_f1'],
            'delta_utility_per_sample': results[1]['utility_per_sample'] - results[0]['utility_per_sample'],
            'usage': {'baseline': old_summary['usage'], 'candidate': new_summary['usage']},
            'note': 'Descriptive paired results, not a significance test or proof of equilibrium. Compare equal budgets.'}
