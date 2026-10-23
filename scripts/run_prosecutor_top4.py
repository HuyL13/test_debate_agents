import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from urllib.request import Request, urlopen

sys.path.insert(0, '.')
from src.data.loader import load_split
from src.labels import FALLACIES, normalize_fallacy_name

# Load env variables
env_path = Path('.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ.get('MARKET_API_KEY')
if not api_key:
    raise RuntimeError("MARKET_API_KEY environment variable not set")

BASE_URL = 'https://mkp-api.fptcloud.com/v1/chat/completions'
MODEL_NAME = 'Llama-3.3-70B-Instruct'

SYSTEM_PROMPT = """You are an expert argumentation logician evaluating logical fallacies in online discourse using the 8-class closed CoCoLoFa taxonomy:
1. Appeal to Authority
2. Appeal to Majority
3. Appeal to Nature
4. Appeal to Tradition
5. Appeal to Worse Problems
6. False Dilemma
7. Hasty Generalization
8. Slippery Slope

TASK:
Analyze the TARGET comment and identify the TOP-4 most plausible fallacy classes from the taxonomy, ranked in descending order of likelihood from Rank 1 (best match) to Rank 4.

Return ONLY a valid JSON object matching this schema:
{
  "top_4": [
    {"rank": 1, "class": "<Class 1>", "quote": "<exact quote from target comment>", "defect_mechanism": "<why this defect applies>"},
    {"rank": 2, "class": "<Class 2>", "quote": "<exact quote from target comment>", "defect_mechanism": "<competing mechanism>"},
    {"rank": 3, "class": "<Class 3>", "quote": "<quote or key phrase>", "defect_mechanism": "<mechanism>"},
    {"rank": 4, "class": "<Class 4>", "quote": "<quote or key phrase>", "defect_mechanism": "<mechanism>"}
  ]
}
All 4 classes MUST be distinct and chosen strictly from the 8 CoCoLoFa classes."""

def query_prosecutor(sample, max_attempts=3):
    user_prompt = f"""News Article Title: {sample.title}
Parent Comment: {sample.parent_comment or 'None'}
TARGET Comment: {sample.comment}

Analyze the TARGET comment and return the TOP-4 ranked candidate fallacy classes in JSON."""

    payload = {
        'model': MODEL_NAME,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt}
        ],
        'temperature': 0.1,
        'max_tokens': 1024
    }

    body_bytes = json.dumps(payload).encode('utf-8')
    for attempt in range(1, max_attempts + 1):
        try:
            req = Request(BASE_URL, data=body_bytes,
                          headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                          method='POST')
            with urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content']
            return content, data.get('usage', {})
        except Exception as e:
            if attempt == max_attempts:
                raise e
            time.sleep(2 * attempt)

import re

def parse_top4(content):
    text = content.strip()
    clean = text
    if '```json' in clean:
        clean = clean.split('```json')[1].split('```')[0].strip()
    elif '```' in clean:
        clean = clean.split('```')[1].split('```')[0].strip()
    
    items = []
    try:
        data = json.loads(clean)
        items = data.get('top_4') or []
    except Exception:
        # Regex fallback for minor JSON syntax flaws (e.g. malformed brackets)
        # Extract class, quote, defect_mechanism per item
        block_pattern = re.compile(r'\{[^{}]*?"class"\s*:\s*"([^"]+)"[^{}]*?\}', re.DOTALL)
        blocks = block_pattern.findall(clean)
        if blocks:
            # Re-find full matches to extract quote and defect
            for m in re.finditer(r'\{([^{}]*?"class"\s*:\s*"[^"]+"[^{}]*?)\}', clean, re.DOTALL):
                b_text = m.group(1)
                c_match = re.search(r'"class"\s*:\s*"([^"]+)"', b_text)
                q_match = re.search(r'"quote"\s*:\s*"([^"]*)"', b_text)
                d_match = re.search(r'"defect_mechanism"\s*:\s*"([^"]*)"', b_text)
                items.append({
                    'class': c_match.group(1) if c_match else '',
                    'quote': q_match.group(1) if q_match else '',
                    'defect_mechanism': d_match.group(1) if d_match else ''
                })
        else:
            # Fallback to direct class extraction
            classes = re.findall(r'"class"\s*:\s*"([^"]+)"', text)
            for c in classes:
                items.append({'class': c, 'quote': '', 'defect_mechanism': ''})

    ranks = []
    quotes = []
    mechanisms = []
    for it in items:
        raw_cls = it.get('class', '')
        norm = normalize_fallacy_name(raw_cls)
        if norm and norm in list(FALLACIES):
            cls_name = norm
        else:
            cls_name = raw_cls
        if cls_name and cls_name not in ranks:
            ranks.append(cls_name)
            quotes.append(it.get('quote', ''))
            mechanisms.append(it.get('defect_mechanism', ''))
    return ranks, quotes, mechanisms


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--output-dir', type=str, default='outputs/prosecutor_top4_llama70b_test481')
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / 'predictions.jsonl'
    summary_path = out_dir / 'summary.json'

    # Load test gold samples
    all_samples = load_split('data/cocolofa/test.json')
    test_samples = [s for s in all_samples if s.fallacy != 'none']
    if args.limit:
        test_samples = test_samples[:args.limit]

    # Resume check
    completed = {}
    if pred_path.exists():
        with open(pred_path, encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    completed[rec['sample_id']] = rec
                except:
                    pass

    print(f"Total target samples: {len(test_samples)} | Already completed: {len(completed)}")

    remaining = [s for s in test_samples if s.sample_id not in completed]
    print(f"Remaining to process: {len(remaining)} with {args.workers} workers...")

    write_lock = Lock()
    stats = {
        'total': len(test_samples),
        'processed': len(completed),
        'top1_correct': sum(1 for r in completed.values() if r['gold'].lower() in [x.lower() for x in r['ranks'][:1]]),
        'top2_correct': sum(1 for r in completed.values() if r['gold'].lower() in [x.lower() for x in r['ranks'][:2]]),
        'top3_correct': sum(1 for r in completed.values() if r['gold'].lower() in [x.lower() for x in r['ranks'][:3]]),
        'top4_correct': sum(1 for r in completed.values() if r['gold'].lower() in [x.lower() for x in r['ranks'][:4]]),
    }

    def process_sample(s):
        gold = s.fallacy
        try:
            content, usage = query_prosecutor(s)
            ranks, quotes, mechanisms = parse_top4(content)
        except Exception as e:
            print(f"Error on {s.sample_id}: {e}")
            ranks, quotes, mechanisms = [], [], []

        record = {
            'sample_id': s.sample_id,
            'gold': gold,
            'title': s.title,
            'comment': s.comment,
            'ranks': ranks,
            'quotes': quotes,
            'mechanisms': mechanisms,
            'top1_hit': gold.lower() in [x.lower() for x in ranks[:1]],
            'top2_hit': gold.lower() in [x.lower() for x in ranks[:2]],
            'top3_hit': gold.lower() in [x.lower() for x in ranks[:3]],
            'top4_hit': gold.lower() in [x.lower() for x in ranks[:4]],
            'raw_response': content if 'content' in locals() else '',
        }

        with write_lock:
            with open(pred_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            stats['processed'] += 1
            if record['top1_hit']: stats['top1_correct'] += 1
            if record['top2_hit']: stats['top2_correct'] += 1
            if record['top3_hit']: stats['top3_correct'] += 1
            if record['top4_hit']: stats['top4_correct'] += 1

            n = stats['processed']
            if n % 10 == 0 or n == stats['total']:
                t1 = stats['top1_correct'] / n * 100
                t2 = stats['top2_correct'] / n * 100
                t3 = stats['top3_correct'] / n * 100
                t4 = stats['top4_correct'] / n * 100
                print(f"[{n}/{stats['total']}] Top-1: {t1:.2f}% | Top-2: {t2:.2f}% | Top-3: {t3:.2f}% | Top-4: {t4:.2f}%")

        return record

    if remaining:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_sample, s) for s in remaining]
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as e:
                    print(f"Future error: {e}")

    # Compute final metrics
    final_records = []
    with open(pred_path, encoding='utf-8') as f:
        for line in f:
            final_records.append(json.loads(line))

    N = len(final_records)
    t1_cnt = sum(1 for r in final_records if r['top1_hit'])
    t2_cnt = sum(1 for r in final_records if r['top2_hit'])
    t3_cnt = sum(1 for r in final_records if r['top3_hit'])
    t4_cnt = sum(1 for r in final_records if r['top4_hit'])

    summary = {
        'total_samples': N,
        'top1_accuracy': t1_cnt / N,
        'top2_accuracy': t2_cnt / N,
        'top3_accuracy': t3_cnt / N,
        'top4_accuracy': t4_cnt / N,
        'top1_count': t1_cnt,
        'top2_count': t2_cnt,
        'top3_count': t3_cnt,
        'top4_count': t4_cnt,
        'per_class': {}
    }

    for f_class in list(FALLACIES):
        sub = [r for r in final_records if r['gold'].lower() == f_class.lower()]
        cnt = len(sub)
        if cnt > 0:
            summary['per_class'][f_class] = {
                'support': cnt,
                'top1_acc': sum(1 for r in sub if r['top1_hit']) / cnt,
                'top2_acc': sum(1 for r in sub if r['top2_hit']) / cnt,
                'top3_acc': sum(1 for r in sub if r['top3_hit']) / cnt,
                'top4_acc': sum(1 for r in sub if r['top4_hit']) / cnt,
            }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "="*50)
    print("FINAL TOP-K EVALUATION RESULTS (PROSECUTOR ONLY)")
    print("="*50)
    print(f"Total Samples Evaluated: {N}")
    print(f"Top-1 Accuracy : {t1_cnt}/{N} ({t1_cnt/N*100:.2f}%)")
    print(f"Top-2 Accuracy : {t2_cnt}/{N} ({t2_cnt/N*100:.2f}%)")
    print(f"Top-3 Accuracy : {t3_cnt}/{N} ({t3_cnt/N*100:.2f}%)")
    print(f"Top-4 Accuracy : {t4_cnt}/{N} ({t4_cnt/N*100:.2f}%)")
    print("="*50)

if __name__ == '__main__':
    main()
