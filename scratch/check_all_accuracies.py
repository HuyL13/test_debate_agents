import json
from pathlib import Path

outputs_dir = Path('outputs')
results = []
for p in outputs_dir.glob('*/summary.json'):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        task = data.get('task')
        count = data.get('count')
        acc = data.get('accuracy')
        mf1 = data.get('macro_f1')
        status = data.get('status')
        model = data.get('model_versions', ['unknown'])
        results.append({
            'dir': p.parent.name,
            'task': task,
            'count': count,
            'accuracy': acc,
            'macro_f1': mf1,
            'status': status,
            'model': model
        })
    except Exception as e:
        pass

cls_results = [r for r in results if r['task'] == 'classification']
cls_results.sort(key=lambda x: (x['accuracy'] if x['accuracy'] is not None else -1), reverse=True)

print(f"=== ALL CLASSIFICATION RUNS ({len(cls_results)}) ===")
for r in cls_results:
    acc_str = f"{r['accuracy']*100:.2f}%" if r['accuracy'] is not None else "N/A"
    mf1_str = f"{r['macro_f1']:.4f}" if r['macro_f1'] is not None else "N/A"
    print(f"- {r['dir']}: Accuracy={acc_str}, Macro-F1={mf1_str}, Count={r['count']}, Status={r['status']}, Model={r['model']}")

# Also let's check reports folder for any frozen benchmarks
reports_dir = Path('reports')
frozen_runs = []
for p in reports_dir.glob('*.json'):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'accuracy' in data:
            frozen_runs.append((p.name, data.get('task'), data.get('count'), data.get('accuracy'), data.get('macro_f1')))
    except Exception:
        pass

if frozen_runs:
    print("\n=== FROZEN BENCHMARKS IN REPORTS ===")
    for name, task, count, acc, mf1 in frozen_runs:
        print(f"- {name}: Task={task}, Count={count}, Acc={acc*100 if acc else 'N/A'}%, Macro-F1={mf1}")
