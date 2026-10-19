import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

traces = json.loads(Path('reports/traces_adversarial_marketplace_llama70b_full.json').read_text(encoding='utf-8'))

for target_class in ['Slippery Slope', 'Hasty Generalization']:
    print(f"=== LLAMA-3.3-70B: {target_class.upper()} ===")
    golds = [t for t in traces if t['gold'] == target_class]
    preds = [t for t in traces if t.get('prediction') == target_class]
    tp = [t for t in traces if t['gold'] == target_class and t.get('prediction') == target_class]
    fn = [t for t in traces if t['gold'] == target_class and t.get('prediction') != target_class]
    fp = [t for t in traces if t['gold'] != target_class and t.get('prediction') == target_class]
    
    print(f"Total Gold: {len(golds)} | TP: {len(tp)} | FN: {len(fn)} | FP: {len(fp)}")
    print(f"Precision: {len(tp)/len(preds)*100:.1f}% | Recall: {len(tp)/len(golds)*100:.1f}% | F1: {2*len(tp)/(len(preds)+len(golds))*100:.1f}%")
    
    if fn:
        print(f"\n--- False Negatives ({len(fn)} mẫu BỊ BỎ SÓT - Gold là {target_class}) ---")
        for t in fn:
            sid = t['sample_id']
            pros = t.get('prosecutor', {})
            cand = pros.get('candidate_class')
            defen = t.get('defender', {})
            alt = defen.get('alternative_class')
            concede = defen.get('concede_charge')
            final = t.get('prediction')
            step = "Prosecutor không khởi tố" if cand != target_class else "Prosecutor đúng nhưng Arbiter lật"
            print(f"  [{sid}] Pros={cand} | Def alt={alt} (concede={concede}) | Final={final} => Bước sai: {step}")
    else:
        print(f"\n--- False Negatives: KHÔNG CÓ (0 mẫu bị bỏ sót! Recall 100%) ---")
        
    if fp:
        print(f"\n--- False Positives ({len(fp)} mẫu ĐOÁN NHẦM THÀNH {target_class} - Gold là lớp khác) ---")
        for t in fp:
            sid = t['sample_id']
            gold = t['gold']
            pros = t.get('prosecutor', {})
            cand = pros.get('candidate_class')
            defen = t.get('defender', {})
            alt = defen.get('alternative_class')
            concede = defen.get('concede_charge')
            final = t.get('prediction')
            step = "Prosecutor khởi tố nhầm" if cand == target_class else "Defender/Arbiter đổi nhầm sang " + target_class
            print(f"  [{sid}] Gold={gold} | Pros={cand} | Def alt={alt} (concede={concede}) | Final={final} => Bước sai: {step}")
            
    print("\n" + "="*80 + "\n")
