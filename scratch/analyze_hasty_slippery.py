import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def analyze(model_name, trace_path):
    traces = json.loads(Path(trace_path).read_text(encoding='utf-8'))
    print(f"\n######################################################################")
    print(f"MODEL: {model_name}")
    print(f"######################################################################")
    
    for target_class in ['Slippery Slope', 'Hasty Generalization']:
        print(f"\n============================== {target_class.upper()} ==============================")
        golds = [t for t in traces if t['gold'] == target_class]
        preds = [t for t in traces if t.get('prediction') == target_class]
        tp = [t for t in traces if t['gold'] == target_class and t.get('prediction') == target_class]
        fn = [t for t in traces if t['gold'] == target_class and t.get('prediction') != target_class]
        fp = [t for t in traces if t['gold'] != target_class and t.get('prediction') == target_class]
        
        prec = len(tp) / len(preds) if preds else 0
        rec = len(tp) / len(golds) if golds else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        
        print(f"Metrics: Prec={prec*100:.1f}%, Rec={rec*100:.1f}% ({len(tp)}/{len(golds)}), F1={f1*100:.1f}%")
        print(f"False Negatives (Bỏ sót - Đúng là {target_class} nhưng đoán nhầm sang lớp khác): {len(fn)}")
        for t in fn:
            sid = t['sample_id']
            cand = t.get('prosecutor', {}).get('candidate_class')
            defen = t.get('defender', {})
            concede = defen.get('concede_charge')
            alt = defen.get('alternative_class')
            pred = t.get('prediction')
            # Check step
            pros_correct = (cand == target_class)
            step_error = "Prosecutor chọn sai ngay từ đầu" if not pros_correct else "Prosecutor đúng nhưng Defender/Arbiter lật sai"
            print(f"  - [{sid}] Pros={cand} | Def alt={alt} (concede={concede}) | Final={pred} => Lỗi ở: {step_error}")
            
        print(f"False Positives (Đoán nhầm thành {target_class} nhưng Gold là lớp khác): {len(fp)}")
        for t in fp:
            sid = t['sample_id']
            gold = t['gold']
            cand = t.get('prosecutor', {}).get('candidate_class')
            defen = t.get('defender', {})
            concede = defen.get('concede_charge')
            alt = defen.get('alternative_class')
            step_error = "Prosecutor khởi tố nhầm thành " + target_class if cand == target_class else "Defender đề xuất nhầm và Arbiter đồng thuận"
            print(f"  - [{sid}] Gold={gold} | Pros={cand} | Def alt={alt} (concede={concede}) => Lỗi ở: {step_error}")

analyze("Llama-3.3-70B-Instruct (Marketplace)", "reports/traces_adversarial_marketplace_llama70b_full.json")
analyze("Llama-3.2-11B V4 (NVIDIA)", "reports/traces_adversarial_v4_full.json")
analyze("GPT-OSS-120B (Marketplace)", "reports/traces_adversarial_marketplace_gptoss120b_full.json")
