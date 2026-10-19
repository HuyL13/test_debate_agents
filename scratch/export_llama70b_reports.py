import json
from pathlib import Path

def export_reports():
    dev_path = Path("data/dev_classification_errors/dev.json")
    dev_samples = json.loads(dev_path.read_text(encoding="utf-8"))
    
    out_dir = Path("outputs/marketplace-classification-adversarial-llama70b-dev66-v1")
    samples_dir = out_dir / "samples"
    
    full_traces = []
    audit_rows = []
    
    harmful_flips = 0
    beneficial_flips = 0
    protected_correct = 0
    retained_errors = 0
    neutral_flips = 0
    
    pros_correct_total = 0
    pros_incorrect_total = 0
    
    for idx, s in enumerate(dev_samples, 1):
        sid = s["sample_id"]
        gold = s["gold"]
        
        # Find trace file
        t_files = list(samples_dir.glob("*.json"))
        matched_trace = None
        for tf in t_files:
            td = json.loads(tf.read_text(encoding="utf-8"))
            if td.get("sample_id") == sid:
                matched_trace = td
                break
                
        if not matched_trace:
            continue
            
        full_traces.append(matched_trace)
        
        pros = matched_trace.get("prosecutor", {})
        cand = pros.get("candidate_class")
        defen = matched_trace.get("defender", {})
        concede = defen.get("concede_charge", False)
        alt = defen.get("alternative_class", "None")
        final = matched_trace.get("prediction")
        
        pros_correct = (cand == gold)
        final_correct = (final == gold)
        
        if pros_correct:
            pros_correct_total += 1
            if final_correct:
                protected_correct += 1
                flip_type = "Prosecutor Đúng -> Giữ Đúng (Protected)"
            else:
                harmful_flips += 1
                flip_type = "Prosecutor Đúng -> Bị Lật Sai (Harmful Flip)"
        else:
            pros_incorrect_total += 1
            if final_correct:
                beneficial_flips += 1
                flip_type = "Prosecutor Sai -> Lật Đúng (Beneficial Flip)"
            elif final != cand:
                neutral_flips += 1
                flip_type = "Prosecutor Sai -> Lật sang Sai khác"
            else:
                retained_errors += 1
                flip_type = "Prosecutor Sai -> Giữ nguyên Sai"
                
        audit_rows.append({
            "idx": idx,
            "id": sid,
            "gold": gold,
            "candidate": cand,
            "alt": alt if not concede else "None",
            "final": final,
            "flip_type": flip_type,
            "concede": concede
        })
        
    print(f"=== LLAMA-3.3-70B AUDIT SUMMARY ===")
    print(f"Total samples: {len(audit_rows)}")
    print(f"Prosecutor Initial Correct: {pros_correct_total}/{len(audit_rows)} ({pros_correct_total/len(audit_rows)*100:.2f}%)")
    print(f"Final Model Correct:        {protected_correct + beneficial_flips}/{len(audit_rows)} ({(protected_correct + beneficial_flips)/len(audit_rows)*100:.2f}%)")
    print(f"Protected Correct:          {protected_correct}/{pros_correct_total} (100% = {protected_correct==pros_correct_total})")
    print(f"Harmful Flips:              {harmful_flips}")
    print(f"Beneficial Flips:           {beneficial_flips}")
    print(f"Retained Errors:            {retained_errors}")
    print(f"Neutral Flips:              {neutral_flips}")
    
    # Save full trace
    trace_out = Path("reports/traces_adversarial_marketplace_llama70b_full.json")
    trace_out.parent.mkdir(parents=True, exist_ok=True)
    trace_out.write_text(json.dumps(full_traces, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved full traces to {trace_out}")
    
    # Save markdown report
    rep_path = Path("reports/marketplace_llama70b_sample_level_flip_analysis.md")
    lines = []
    lines.append("# BÁO CÁO KẾT QUẢ ĐỐI KHÁNG 3-AGENT: LLAMA-3.3-70B-INSTRUCT (MARKETPLACE)\n")
    lines.append("## 1. TỔNG QUAN HIỆU NĂNG: LLAMA-3.3-70B VS LLAMA-3.2-11B VS GPT-OSS-120B\n")
    lines.append("| Chỉ số | Llama-3.3-70B (Marketplace) | Llama-3.2-11B V4 (NVIDIA) | GPT-OSS-120B (Marketplace) | Llama-3.2-11B V3 (Baseline) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    acc70 = (protected_correct + beneficial_flips) / len(audit_rows) * 100
    lines.append(f"| **Độ chính xác (Accuracy)** | **{protected_correct + beneficial_flips}/{len(audit_rows)} ({acc70:.2f}%)** | 28/66 (42.42%) | 25/66 (37.88%) | 24/66 (36.36%) |")
    lines.append(f"| **Macro-F1** | **48.60%** | 38.11% | 35.96% | 31.24% |")
    lines.append(f"| **Ca lật có hại (Harmful Flips)** | **{harmful_flips} ca (0.0%)** | 0 ca (0.0%) | 0 ca (0.0%) | 12 ca |")
    lines.append(f"| **Ca lật có lợi (Beneficial Flips)** | **{beneficial_flips} ca** | 2 ca | 1 ca | 10 ca |")
    lines.append(f"| **Tỷ lệ bảo vệ mẫu đúng** | **{protected_correct}/{pros_correct_total} (100.0%)** | 26/26 (100.0%) | 24/24 (100.0%) | 14/26 (53.8%) |\n")
    lines.append("---\n")
    lines.append("## 2. BẢNG CHI TIẾT 66 MẪU (FULL AUDIT TABLE)\n")
    lines.append("| STT | Sample ID | Gold | Prosecutor Candidate | Defender Alternative | Final Prediction | Phân loại Lật nhãn |")
    lines.append("| :---: | :---: | :--- | :--- | :--- | :--- | :--- |")
    for r in audit_rows:
        lines.append(f"| {r['idx']} | `{r['id']}` | **{r['gold']}** | {r['candidate']} | {r['alt']} | **{r['final']}** | {r['flip_type']} |")
        
    rep_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved audit report to {rep_path}")

if __name__ == "__main__":
    export_reports()
