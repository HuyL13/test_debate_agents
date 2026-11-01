"""Strict metrics; no silent dropping of failed predictions."""
import argparse
import json
from collections import Counter

from src.io_utils import read_jsonl, write_json
from src.labels import labels_for


def score(records):
    if not records:
        raise ValueError('No predictions to evaluate')
    tasks = {r['task'] for r in records}
    if len(tasks) != 1:
        raise ValueError('Cannot mix tasks')
    task = next(iter(tasks))
    labels = labels_for(task)
    matrix = [[0 for _ in labels] for _ in labels]
    seen = set()
    for row in records:
        if row['sample_id'] in seen:
            raise ValueError('Duplicate sample prediction')
        seen.add(row['sample_id'])
        if row.get('status', 'ok') != 'ok':
            raise ValueError('Failed samples present; resume the run before scoring')
        if row['gold'] not in labels or row['prediction'] not in labels:
            raise ValueError('Prediction/gold outside task label space')
        matrix[labels.index(row['gold'])][labels.index(row['prediction'])] += 1
    per_class = {}
    for i, label in enumerate(labels):
        tp = matrix[i][i]
        support = sum(matrix[i])
        predicted = sum(row[i] for row in matrix)
        p = tp / predicted if predicted else 0.0
        r = tp / support if support else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        per_class[label] = {'precision': p, 'recall': r, 'f1': f1, 'support': support}
    result = {'task': task, 'count': len(records), 'labels': list(labels),
              'confusion_matrix': matrix, 'per_class': per_class,
              'accuracy': sum(matrix[i][i] for i in range(len(labels))) / len(records),
              'zero_division': 0}
    if task == 'detection':
        result.update({k: per_class['Fallacious'][k] for k in ('precision', 'recall', 'f1')})
        non_idx = labels.index('Non-Fallacious')
        fall_idx = labels.index('Fallacious')
        tn = matrix[non_idx][non_idx]
        fp = matrix[non_idx][fall_idx]
        fn = matrix[fall_idx][non_idx]
        tp = matrix[fall_idx][fall_idx]
        result.update({'gold_fallacious_rate': (tp + fn) / len(records),
                       'predicted_fallacious_rate': (tp + fp) / len(records),
                       'false_positive_rate': fp / (fp + tn) if fp + tn else 0.0,
                       'false_negative_rate': fn / (fn + tp) if fn + tp else 0.0})
    else:
        result['macro_f1'] = sum(v['f1'] for v in per_class.values()) / 8
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    from src.runner import evaluate_run
    result = evaluate_run(args.predictions)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
