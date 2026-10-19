import json
from pathlib import Path
from src.fallacy_cues import has_class_cue

v4_dir = Path('outputs/nvidia-classification-adversarial-llama11b-dev66-v4/samples')
v4_traces = [json.loads(p.read_text(encoding='utf-8')) for p in v4_dir.glob('*.json') if json.loads(p.read_text(encoding='utf-8')).get('status') == 'ok']

for t in v4_traces:
    d = t.get('defender', {})
    interp = d.get('charitable_interpretation', '')
    if "lacks required structural cue" in interp:
        sid = t['sample_id']
        gold = t['gold']
        cand = t.get('prosecutor', {}).get('candidate_class')
        alt = d.get('alternative_class')
        quote = d.get('counter_quote')
        comment = t.get('input', {}).get('comment') or t.get('comment') or t.get('target_comment', '')
        print(f"[{sid}] Gold: {gold} | Pros Cand: {cand} | Def Alt: {alt}")
        print(f"  Comment: {repr(comment)}")
        print(f"  Def Quote: {repr(quote)}")
        print(f"  Cue in quote: {has_class_cue(alt, quote)}")
        print(f"  Cue in comment: {has_class_cue(alt, comment)}")
        print(f"  Interp: {interp[:120]}")
        print()
