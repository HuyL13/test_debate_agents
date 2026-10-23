import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.data.loader import load_split
def load_raw_calls(path):
    calls_by_sid = {}
    if not path.exists():
        return calls_by_sid
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            meta = rec.get('metadata', {})
            sid = meta.get('sample_id')
            if not sid:
                continue
            role = meta.get('role', 'Unknown')
            stage = meta.get('stage', '')
            choice = (rec.get('response', {}).get('choices') or [{}])[0].get('message', {})
            usage = rec.get('response', {}).get('usage', {})
            # 1. Native reasoning field (e.g. OpenAI o1 / DeepSeek-R1 / gpt-oss-120b style)
            reasoning = choice.get('reasoning_content') or ''

            # 2. Pre-JSON chain-of-thought in text content (e.g. Llama-3.3-70B-Instruct)
            if not reasoning:
                content = choice.get('content') or ''
                if '```' in content:
                    pre = content.split('```')[0].strip()
                    if len(pre) > 30:
                        reasoning = pre

            calls_by_sid.setdefault(sid, {})[role] = {
                'role': role,
                'stage': stage,
                'latency': rec.get('latency_seconds', 0),
                'content': choice.get('content', ''),
                'reasoning_content': reasoning,
                'usage': usage
            }
    return calls_by_sid

def main():
    # 1. Load ground truth test samples
    print("Loading test samples from data/cocolofa/test.json...")
    test_samples = load_split('data/cocolofa/test.json')
    test_dict = {s.sample_id: s for s in test_samples if s.fallacy != 'none'}
    print(f"Loaded {len(test_dict)} gold classification test samples.")

    # 2. Load predictions and raw API calls from Llama-70B and GPT-120B
    llama_path = Path('outputs/marketplace-classification-adversarial-llama70b-test481-v1/predictions.jsonl')
    gpt_path = Path('outputs/marketplace-classification-adversarial-gptoss120b-test481-v1/predictions.jsonl')
    llama_raw_path = Path('outputs/marketplace-classification-adversarial-llama70b-test481-v1/raw_calls.jsonl')
    gpt_raw_path = Path('outputs/marketplace-classification-adversarial-gptoss120b-test481-v1/raw_calls.jsonl')

    print("Indexing raw_calls.jsonl (API-level calls & chain-of-thought)...")
    llama_raw = load_raw_calls(llama_raw_path)
    gpt_raw = load_raw_calls(gpt_raw_path)
    print(f"Indexed raw calls for {len(llama_raw)} Llama samples and {len(gpt_raw)} GPT samples.")

    llama_preds = {}
    with open(llama_path, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            llama_preds[r['sample_id']] = r

    gpt_preds = {}
    with open(gpt_path, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            gpt_preds[r['sample_id']] = r

    print(f"Loaded {len(llama_preds)} Llama-70B predictions and {len(gpt_preds)} GPT-120B predictions.")

    # 3. Assemble combined records
    combined_records = []
    stats = {
        'total': len(test_dict),
        'llama_correct': 0,
        'gpt_correct': 0,
        'both_correct': 0,
        'both_incorrect': 0,
        'llama_only_correct': 0,
        'gpt_only_correct': 0,
        'llama_conceded': 0,
        'llama_contested': 0,
        'gpt_conceded': 0,
        'gpt_contested': 0,
    }

    for sid, s in test_dict.items():
        gold = s.fallacy
        l_rec = llama_preds.get(sid, {})
        g_rec = gpt_preds.get(sid, {})

        l_raw_calls = llama_raw.get(sid, {})
        g_raw_calls = gpt_raw.get(sid, {})

        l_pred = l_rec.get('prediction', '')
        g_pred = g_rec.get('prediction', '')

        l_corr = (l_pred.lower() == gold.lower())
        g_corr = (g_pred.lower() == gold.lower())

        if l_corr: stats['llama_correct'] += 1
        if g_corr: stats['gpt_correct'] += 1
        if l_corr and g_corr: stats['both_correct'] += 1
        elif not l_corr and not g_corr: stats['both_incorrect'] += 1
        elif l_corr and not g_corr: stats['llama_only_correct'] += 1
        elif not l_corr and g_corr: stats['gpt_only_correct'] += 1

        l_def = l_rec.get('defender', {}) or {}
        g_def = g_rec.get('defender', {}) or {}

        l_conceded = l_def.get('concede_charge', False)
        g_conceded = g_def.get('concede_charge', False)

        if l_conceded: stats['llama_conceded'] += 1
        else: stats['llama_contested'] += 1

        if g_conceded: stats['gpt_conceded'] += 1
        else: stats['gpt_contested'] += 1

        rec = {
            'sample_id': sid,
            'gold': gold,
            'title': s.title,
            'parent_comment': s.parent_comment,
            'target_comment': s.comment,
            'agreement_status': 'both_correct' if (l_corr and g_corr) else ('both_incorrect' if (not l_corr and not g_corr) else ('llama_only' if l_corr else 'gpt_only')),
            'llama_70b': {
                'prediction': l_pred,
                'is_correct': l_corr,
                'confidence': (l_rec.get('arbiter') or {}).get('confidence', 1.0 if l_conceded else 0.8),
                'prosecutor': {
                    'candidate_class': (l_rec.get('prosecutor') or {}).get('candidate_class', ''),
                    'defect_mechanism': (l_rec.get('prosecutor') or {}).get('defect_mechanism', ''),
                    'quote': (l_rec.get('prosecutor') or {}).get('quote', ''),
                    'runner_up_class': (l_rec.get('prosecutor') or {}).get('runner_up_class', ''),
                    'runner_up_defect': (l_rec.get('prosecutor') or {}).get('runner_up_defect', ''),
                    'runner_up_quote': (l_rec.get('prosecutor') or {}).get('runner_up_quote', ''),
                    'reasoning_content': l_raw_calls.get('Prosecutor', {}).get('reasoning_content', '')
                },
                'defender': {
                    'concede_charge': l_conceded,
                    'charitable_interpretation': l_def.get('charitable_interpretation', ''),
                    'alternative_class': l_def.get('alternative_class', ''),
                    'counter_quote': l_def.get('counter_quote', ''),
                    'reasoning_content': l_raw_calls.get('Defender', {}).get('reasoning_content', '')
                },
                'arbiter': {
                    'prediction': (l_rec.get('arbiter') or {}).get('prediction', ''),
                    'confidence': (l_rec.get('arbiter') or {}).get('confidence', None),
                    'content': (l_rec.get('arbiter') or {}).get('content', ''),
                    'reasoning_content': l_raw_calls.get('DialecticalArbiter', {}).get('reasoning_content', '')
                }
            },
            'gpt_oss_120b': {
                'prediction': g_pred,
                'is_correct': g_corr,
                'confidence': (g_rec.get('arbiter') or {}).get('confidence', 1.0 if g_conceded else 0.8),
                'prosecutor': {
                    'candidate_class': (g_rec.get('prosecutor') or {}).get('candidate_class', ''),
                    'defect_mechanism': (g_rec.get('prosecutor') or {}).get('defect_mechanism', ''),
                    'quote': (g_rec.get('prosecutor') or {}).get('quote', ''),
                    'runner_up_class': (g_rec.get('prosecutor') or {}).get('runner_up_class', ''),
                    'runner_up_defect': (g_rec.get('prosecutor') or {}).get('runner_up_defect', ''),
                    'runner_up_quote': (g_rec.get('prosecutor') or {}).get('runner_up_quote', ''),
                    'reasoning_content': g_raw_calls.get('Prosecutor', {}).get('reasoning_content', '')
                },
                'defender': {
                    'concede_charge': g_conceded,
                    'charitable_interpretation': g_def.get('charitable_interpretation', ''),
                    'alternative_class': g_def.get('alternative_class', ''),
                    'counter_quote': g_def.get('counter_quote', ''),
                    'reasoning_content': g_raw_calls.get('Defender', {}).get('reasoning_content', '')
                },
                'arbiter': {
                    'prediction': (g_rec.get('arbiter') or {}).get('prediction', ''),
                    'confidence': (g_rec.get('arbiter') or {}).get('confidence', None),
                    'content': (g_rec.get('arbiter') or {}).get('content', ''),
                    'reasoning_content': g_raw_calls.get('DialecticalArbiter', {}).get('reasoning_content', '')
                }
            }
        }
        combined_records.append(rec)

    # 4. Save JSON
    reports_dir = Path('reports')
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / 'full_test_debate_traces_481_both_models.json'
    json_path.write_text(json.dumps({'summary_stats': stats, 'samples': combined_records}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Saved full JSON log: {json_path.resolve()} ({json_path.stat().st_size} bytes)")

    # 5. Save comprehensive Markdown Log
    md_path = reports_dir / 'full_test_debate_traces_481_both_models.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Full Adversarial Dialectical Multi-Agent Debate Log: CoCoLoFa Test Set (481 Samples)\n\n")
        f.write("## 1. Summary Benchmark Comparison\n\n")
        f.write(f"- **Total Samples:** {stats['total']}\n")
        f.write(f"- **Llama-3.3-70B-Instruct:** {stats['llama_correct']} / {stats['total']} ({stats['llama_correct']/stats['total']*100:.2f}% Accuracy)\n")
        f.write(f"- **gpt-oss-120b:** {stats['gpt_correct']} / {stats['total']} ({stats['gpt_correct']/stats['total']*100:.2f}% Accuracy)\n")
        f.write(f"- **Both Models Correct:** {stats['both_correct']} ({stats['both_correct']/stats['total']*100:.2f}%)\n")
        f.write(f"- **Both Models Incorrect:** {stats['both_incorrect']} ({stats['both_incorrect']/stats['total']*100:.2f}%)\n")
        f.write(f"- **Llama Correct / GPT Incorrect:** {stats['llama_only_correct']}\n")
        f.write(f"- **GPT Correct / Llama Incorrect:** {stats['gpt_only_correct']}\n")
        f.write(f"- **Llama Fast-Path Concessions:** {stats['llama_conceded']} ({stats['llama_conceded']/stats['total']*100:.2f}%) | Contested: {stats['llama_contested']}\n")
        f.write(f"- **GPT Fast-Path Concessions:** {stats['gpt_conceded']} ({stats['gpt_conceded']/stats['total']*100:.2f}%) | Contested: {stats['gpt_contested']}\n\n")
        f.write("---\n\n")
        f.write("## 2. Exhaustive Per-Sample Transcripts\n\n")

        for idx, rec in enumerate(combined_records, 1):
            sid = rec['sample_id']
            gold = rec['gold']
            l_info = rec['llama_70b']
            g_info = rec['gpt_oss_120b']

            l_mark = "✅" if l_info['is_correct'] else "❌"
            g_mark = "✅" if g_info['is_correct'] else "❌"

            f.write(f"### Case {idx}/{len(combined_records)}: Sample `{sid}` | Gold: **{gold}**\n\n")
            f.write(f"- **Headline ($T$):** {rec['title']}\n")
            if rec['parent_comment']:
                f.write(f"- **Parent Comment ($P$):** {rec['parent_comment']}\n")
            f.write(f"- **Target Comment ($C$):** *\"{rec['target_comment']}\"*\n\n")
            f.write(f"| Model | Verdict | Prediction | Status | Confidence |\n")
            f.write(f"| :--- | :---: | :--- | :---: | :---: |\n")
            f.write(f"| **Llama-3.3-70B** | {l_mark} | {l_info['prediction']} | {'Conceded (Fast-Path)' if l_info['defender']['concede_charge'] else 'Contested (Arbiter)'} | {l_info['confidence']} |\n")
            f.write(f"| **gpt-oss-120b** | {g_mark} | {g_info['prediction']} | {'Conceded (Fast-Path)' if g_info['defender']['concede_charge'] else 'Contested (Arbiter)'} | {g_info['confidence']} |\n\n")

            # Llama agents
            f.write(f"#### 🦙 Llama-3.3-70B Agent Dialogue:\n\n")
            lp = l_info['prosecutor']
            ld = l_info['defender']
            la = l_info['arbiter']

            f.write(f"1. **Prosecutor Agent:**\n")
            f.write(f"   - **Indictment:** `{lp['candidate_class']}`\n")
            f.write(f"   - **Defect Reasoning:** {lp['defect_mechanism']}\n")
            f.write(f"   - **Evidence Quote:** *\"{lp['quote']}\"*\n")
            if lp['runner_up_class']:
                f.write(f"   - **Runner-up:** `{lp['runner_up_class']}` (*\"{lp['runner_up_quote']}\"*)\n")
            if lp.get('reasoning_content'):
                f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {lp['reasoning_content'].strip()}\n     ```\n     </details>\n")

            f.write(f"\n2. **Defender Agent:**\n")
            f.write(f"   - **Plea:** `{'CONCEDED' if ld['concede_charge'] else 'CONTESTED'}`\n")
            f.write(f"   - **Charitable Interpretation:** {ld['charitable_interpretation']}\n")
            if not ld['concede_charge']:
                f.write(f"   - **Alternative Class:** `{ld['alternative_class']}`\n")
                f.write(f"   - **Counter-Quote:** *\"{ld['counter_quote']}\"*\n")
            if ld.get('reasoning_content'):
                f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {ld['reasoning_content'].strip()}\n     ```\n     </details>\n")

            if not ld['concede_charge'] and la['content']:
                f.write(f"\n3. **Dialectical Arbiter Agent:**\n")
                f.write(f"   - **Ruling:** `{la['prediction']}` (Confidence: {la['confidence']})\n")
                f.write(f"   - **Deliberation:** {la['content']}\n")
                if la.get('reasoning_content'):
                    f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {la['reasoning_content'].strip()}\n     ```\n     </details>\n")

            # GPT agents
            f.write(f"\n#### 🤖 gpt-oss-120b Agent Dialogue:\n\n")
            gp = g_info['prosecutor']
            gd = g_info['defender']
            ga = g_info['arbiter']

            f.write(f"1. **Prosecutor Agent:**\n")
            f.write(f"   - **Indictment:** `{gp['candidate_class']}`\n")
            f.write(f"   - **Defect Reasoning:** {gp['defect_mechanism']}\n")
            f.write(f"   - **Evidence Quote:** *\"{gp['quote']}\"*\n")
            if gp['runner_up_class']:
                f.write(f"   - **Runner-up:** `{gp['runner_up_class']}` (*\"{gp['runner_up_quote']}\"*)\n")
            if gp.get('reasoning_content'):
                f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {gp['reasoning_content'].strip()}\n     ```\n     </details>\n")

            f.write(f"\n2. **Defender Agent:**\n")
            f.write(f"   - **Plea:** `{'CONCEDED' if gd['concede_charge'] else 'CONTESTED'}`\n")
            f.write(f"   - **Charitable Interpretation:** {gd['charitable_interpretation']}\n")
            if not gd['concede_charge']:
                f.write(f"   - **Alternative Class:** `{gd['alternative_class']}`\n")
                f.write(f"   - **Counter-Quote:** *\"{gd['counter_quote']}\"*\n")
            if gd.get('reasoning_content'):
                f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {gd['reasoning_content'].strip()}\n     ```\n     </details>\n")

            if not gd['concede_charge'] and ga['content']:
                f.write(f"\n3. **Dialectical Arbiter Agent:**\n")
                f.write(f"   - **Ruling:** `{ga['prediction']}` (Confidence: {ga['confidence']})\n")
                f.write(f"   - **Deliberation:** {ga['content']}\n")
                if ga.get('reasoning_content'):
                    f.write(f"   - <details><summary>🧠 <i>Inner Thinking (raw_calls.jsonl)</i></summary>\n\n     ```\n     {ga['reasoning_content'].strip()}\n     ```\n     </details>\n")

            f.write("\n---\n\n")

    print(f"Saved full Markdown log: {md_path.resolve()} ({md_path.stat().st_size} bytes)")

    # 6. Generate interactive HTML viewer
    html_path = reports_dir / 'debate_log_viewer.html'
    generate_html_viewer(combined_records, stats, html_path)
    print(f"Saved interactive HTML viewer: {html_path.resolve()} ({html_path.stat().st_size} bytes)")

def generate_html_viewer(records, stats, out_path):
    records_json = json.dumps(records, ensure_ascii=False)
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Adversarial Dialectical Debate Full Test Traces (481 Cases)</title>
  <style>
    :root {{
      --primary: #2563eb;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --success: #16a34a;
      --danger: #dc2626;
      --purple: #9333ea;
      --amber: #d97706;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: var(--text);
    }}
    .header {{
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      border: 1px solid var(--border);
      margin-bottom: 24px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    h1 {{ margin: 0 0 10px 0; font-size: 22px; }}
    .subtitle {{ font-size: 14px; color: #475569; margin-bottom: 16px; line-height: 1.5; }}
    .metrics-explanation {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 13px;
      color: #1e40af;
      margin-bottom: 16px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .stat-card {{
      background: #f1f5f9;
      padding: 12px 14px;
      border-radius: 8px;
      border-left: 3px solid #94a3b8;
    }}
    .stat-card.primary {{ border-left-color: var(--primary); }}
    .stat-card.purple {{ border-left-color: var(--purple); }}
    .stat-card.success {{ border-left-color: var(--success); }}
    .stat-card.danger {{ border-left-color: var(--danger); }}
    .stat-label {{ font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }}
    .stat-val {{ font-size: 19px; font-weight: 800; margin-top: 3px; color: #1e293b; }}
    .stat-sub {{ font-size: 11.5px; color: #64748b; margin-top: 2px; }}
    .controls {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 20px;
      align-items: center;
      background: #ffffff;
      padding: 16px;
      border-radius: 10px;
      border: 1px solid var(--border);
    }}
    input, select {{
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 13.5px;
      outline: none;
    }}
    input:focus, select:focus {{ border-color: var(--primary); }}
    .pagination-bar {{
      display: flex;
      gap: 8px;
      align-items: center;
      margin-left: auto;
    }}
    .btn {{
      background: #ffffff;
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      transition: all 0.2s;
    }}
    .btn:hover {{ background: #f1f5f9; border-color: #cbd5e1; }}
    .btn.active {{ background: var(--primary); color: #ffffff; border-color: var(--primary); }}
    .samples-container {{
      display: flex;
      flex-direction: column;
      gap: 20px;
      margin-top: 20px;
    }}
    .sample-card {{
      background: #ffffff;
      border-radius: 10px;
      border: 1px solid var(--border);
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
    }}
    .sample-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
      margin-bottom: 14px;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 16px;
      font-size: 11.5px;
      font-weight: 700;
    }}
    .badge-gold {{ background: #e0e7ff; color: #3730a3; }}
    .badge-correct {{ background: #dcfce7; color: #15803d; }}
    .badge-wrong {{ background: #fee2e2; color: #b91c1c; }}
    .badge-conceded {{ background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }}
    .badge-contested {{ background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }}
    .context-box {{
      background: #f8fafc;
      padding: 12px 16px;
      border-radius: 8px;
      border-left: 4px solid #94a3b8;
      font-size: 13.5px;
      margin-bottom: 16px;
    }}
    .models-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    @media (max-width: 900px) {{
      .models-grid {{ grid-template-columns: 1fr; }}
    }}
    .model-col {{
      background: #fafafa;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
    }}
    .model-title {{
      font-weight: 800;
      font-size: 14.5px;
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .agent-box {{
      background: #ffffff;
      border-radius: 6px;
      border: 1px solid var(--border);
      padding: 12px;
      margin-bottom: 10px;
      font-size: 12.5px;
    }}
    .agent-header {{
      font-weight: 700;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .prosecutor-header {{ color: var(--primary); }}
    .defender-header {{ color: var(--purple); }}
    .arbiter-header {{ color: var(--danger); }}
    .quote-box {{
      background: #f1f5f9;
      padding: 6px 10px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      color: #334155;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🏛️ Adversarial Dialectical Multi-Agent Debate Full Test Logs (All 481 Cases)</h1>
    <div class="subtitle">
      Comprehensive sample-by-sample trace comparing <strong>Llama-3.3-70B-Instruct</strong> and <strong>gpt-oss-120b</strong> on the complete CoCoLoFa test partition.
    </div>

    <!-- Clarification on Precision 88.29% vs Macro-F1 86.77% vs Accuracy 86.90% -->
    <div class="metrics-explanation">
      💡 <strong>Lưu ý về các chỉ số đo lường (Metrics Breakdown):</strong><br>
      • <strong>Precision (Độ chuẩn xác Macro-P):</strong> Llama-3.3-70B đạt <strong>88.29%</strong> (vượt xa GPT-4o CoT 85.0% và NLI 87.0%).<br>
      • <strong>Accuracy (Tỷ lệ đoán đúng tuyệt đối):</strong> <strong>86.90%</strong> (418 / 481 mẫu đoán đúng).<br>
      • <strong>Macro-F1 (Trung bình điều hòa F1 qua 8 lớp):</strong> <strong>86.77%</strong> (gpt-oss-120b đạt 85.83% Macro-F1, 86.07% Accuracy).
    </div>
    
    <div class="stats-grid">
      <div class="stat-card primary">
        <div class="stat-label">Llama-70B Precision</div>
        <div class="stat-val" style="color:#2563eb;">88.29%</div>
        <div class="stat-sub">Macro Precision</div>
      </div>
      <div class="stat-card primary">
        <div class="stat-label">Llama-70B Macro-F1</div>
        <div class="stat-val" style="color:#1d4ed8;">86.77%</div>
        <div class="stat-sub">Macro-F1 Score</div>
      </div>
      <div class="stat-card primary">
        <div class="stat-label">Llama-70B Accuracy</div>
        <div class="stat-val" style="color:#0284c7;">86.90%</div>
        <div class="stat-sub">418 / 481 correct</div>
      </div>
      <div class="stat-card purple">
        <div class="stat-label">GPT-120B Precision</div>
        <div class="stat-val" style="color:#9333ea;">87.29%</div>
        <div class="stat-sub">Macro Precision</div>
      </div>
      <div class="stat-card purple">
        <div class="stat-label">GPT-120B Macro-F1</div>
        <div class="stat-val" style="color:#7e22ce;">85.83%</div>
        <div class="stat-sub">Macro-F1 Score</div>
      </div>
      <div class="stat-card purple">
        <div class="stat-label">GPT-120B Accuracy</div>
        <div class="stat-val" style="color:#a855f7;">86.07%</div>
        <div class="stat-sub">414 / 481 correct</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">Both Correct</div>
        <div class="stat-val" style="color:#16a34a;">{stats['both_correct']}</div>
        <div class="stat-sub">{stats['both_correct']/stats['total']*100:.1f}% consensus</div>
      </div>
      <div class="stat-card danger">
        <div class="stat-label">Both Incorrect</div>
        <div class="stat-val" style="color:#dc2626;">{stats['both_incorrect']}</div>
        <div class="stat-sub">{stats['both_incorrect']/stats['total']*100:.1f}% hard cases</div>
      </div>
    </div>
  </div>

  <div class="controls">
    <input type="text" id="searchInput" placeholder="Search keyword, sample ID..." oninput="handleSearch()" style="width:220px;">
    
    <select id="goldFilter" onchange="handleFilter()">
      <option value="">All Fallacy Classes (8)</option>
      <option value="Appeal to Authority">Appeal to Authority</option>
      <option value="Appeal to Majority">Appeal to Majority</option>
      <option value="Appeal to Nature">Appeal to Nature</option>
      <option value="Appeal to Tradition">Appeal to Tradition</option>
      <option value="Appeal to Worse Problems">Appeal to Worse Problems</option>
      <option value="False Dilemma">False Dilemma</option>
      <option value="Hasty Generalization">Hasty Generalization</option>
      <option value="Slippery Slope">Slippery Slope</option>
    </select>

    <select id="statusFilter" onchange="handleFilter()">
      <option value="">All Outcomes</option>
      <option value="both_correct">Both Correct (397)</option>
      <option value="llama_only">Llama Correct / GPT Wrong (21)</option>
      <option value="gpt_only">GPT Correct / Llama Wrong (17)</option>
      <option value="both_incorrect">Both Incorrect (46)</option>
    </select>

    <select id="pageSizeSelect" onchange="handlePageSizeChange()">
      <option value="100">Show 100 per page</option>
      <option value="50">Show 50 per page</option>
      <option value="250">Show 250 per page</option>
      <option value="all">Show All 481 Cases</option>
    </select>

    <span id="counter" style="font-size:13.5px; font-weight:700; color:var(--text-muted);">Showing 481 samples</span>

    <div class="pagination-bar" id="paginationBar"></div>
  </div>

  <div class="samples-container" id="samplesContainer"></div>

  <script>
    const allData = {records_json};
    let filteredData = allData;
    let currentPage = 1;
    let pageSize = 100;

    function handleSearch() {{
      applyFilters();
    }}

    function handleFilter() {{
      applyFilters();
    }}

    function handlePageSizeChange() {{
      const val = document.getElementById('pageSizeSelect').value;
      pageSize = (val === 'all') ? allData.length : parseInt(val, 10);
      currentPage = 1;
      renderCurrentPage();
    }}

    function applyFilters() {{
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const gold = document.getElementById('goldFilter').value;
      const status = document.getElementById('statusFilter').value;

      filteredData = allData.filter(s => {{
        if (gold && s.gold !== gold) return false;
        if (status && s.agreement_status !== status) return false;
        if (query) {{
          const hay = (s.sample_id + ' ' + s.target_comment + ' ' + s.gold + ' ' + s.llama_70b.prediction + ' ' + s.gpt_oss_120b.prediction).toLowerCase();
          if (!hay.includes(query)) return false;
        }}
        return true;
      }});

      currentPage = 1;
      renderCurrentPage();
    }}

    function goToPage(p) {{
      currentPage = p;
      renderCurrentPage();
      window.scrollTo({{ top: 380, behavior: 'smooth' }});
    }}

    function renderPagination(totalItems) {{
      const bar = document.getElementById('paginationBar');
      if (pageSize >= totalItems) {{
        bar.innerHTML = '<span style="font-size:12px; color:#64748b; font-weight:600;">Showing All ' + totalItems + ' items</span>';
        return;
      }}

      const totalPages = Math.ceil(totalItems / pageSize);
      let html = '';
      
      if (currentPage > 1) {{
        html += `<button class="btn" onclick="goToPage(${{currentPage - 1}})">« Prev</button>`;
      }}

      for (let i = 1; i <= totalPages; i++) {{
        html += `<button class="btn ${{i === currentPage ? 'active' : ''}}" onclick="goToPage(${{i}})">${{i}}</button>`;
      }}

      if (currentPage < totalPages) {{
        html += `<button class="btn" onclick="goToPage(${{currentPage + 1}})">Next »</button>`;
      }}

      bar.innerHTML = html;
    }}

    function renderCurrentPage() {{
      const container = document.getElementById('samplesContainer');
      const total = filteredData.length;
      document.getElementById('counter').innerText = `Total: ${{total}} matching cases`;

      if (total === 0) {{
        container.innerHTML = '<div style="text-align:center; padding:50px; color:#64748b;">No matching cases found.</div>';
        document.getElementById('paginationBar').innerHTML = '';
        return;
      }}

      renderPagination(total);

      const startIdx = (currentPage - 1) * pageSize;
      const endIdx = Math.min(startIdx + pageSize, total);
      const pageSlice = filteredData.slice(startIdx, endIdx);

      container.innerHTML = pageSlice.map((s, idx) => {{
        const globalIdx = startIdx + idx + 1;
        const l = s.llama_70b;
        const g = s.gpt_oss_120b;

        return `
          <div class="sample-card">
            <div class="sample-header">
              <div>
                <strong>Case ${{globalIdx}} / ${{total}}: Sample <code>${{s.sample_id}}</code></strong>
                <span class="badge badge-gold" style="margin-left:8px;">Gold: ${{s.gold}}</span>
              </div>
              <div>
                <span class="badge ${{l.is_correct ? 'badge-correct' : 'badge-wrong'}}">Llama: ${{l.prediction}}</span>
                <span class="badge ${{g.is_correct ? 'badge-correct' : 'badge-wrong'}}" style="margin-left:4px;">GPT: ${{g.prediction}}</span>
              </div>
            </div>

            <div class="context-box">
              <div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:4px;">TARGET COMMENT:</div>
              <div style="font-weight:600; color:#0f172a; line-height:1.45;">"${{s.target_comment}}"</div>
              ${{s.title ? `<div style="font-size:12px; color:#64748b; margin-top:6px;"><strong>Article Headline:</strong> ${{s.title}}</div>` : ''}}
              ${{s.parent_comment ? `<div style="font-size:12px; color:#64748b; margin-top:4px;"><strong>Parent Comment:</strong> ${{s.parent_comment}}</div>` : ''}}
            </div>

            <div class="models-grid">
              <!-- Llama Column -->
              <div class="model-col">
                <div class="model-title">
                  <span>🦙 Llama-3.3-70B-Instruct</span>
                  <span class="badge ${{l.defender.concede_charge ? 'badge-conceded' : 'badge-contested'}}">
                    ${{l.defender.concede_charge ? 'Conceded (Fast-Path)' : 'Contested (Arbiter)'}}
                  </span>
                </div>

                <!-- Prosecutor -->
                <div class="agent-box">
                  <div class="agent-header prosecutor-header">
                    <span>⚡ Prosecutor Agent</span>
                    <span style="font-size:11px; background:#dbeafe; color:#1e40af; padding:1px 6px; border-radius:4px;">
                      Cand: ${{l.prosecutor.candidate_class}}
                    </span>
                  </div>
                  <div><strong>Mechanism:</strong> ${{l.prosecutor.defect_mechanism}}</div>
                  <div class="quote-box">Evidence Quote: "${{l.prosecutor.quote}}"</div>
                  ${{l.prosecutor.runner_up_class ? `<div style="margin-top:6px; font-size:11.5px; color:#64748b;">Runner-up: <strong>${{l.prosecutor.runner_up_class}}</strong> ("${{l.prosecutor.runner_up_quote}}")</div>` : ''}}
                  ${{l.prosecutor.reasoning_content ? `
                    <details style="margin-top:6px;">
                      <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#475569;">🧠 Inner Thinking (raw_calls.jsonl)</summary>
                      <div style="background:#f8fafc; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #e2e8f0; margin-top:4px; font-family:monospace; color:#334155;">${{escapeHtml(l.prosecutor.reasoning_content)}}</div>
                    </details>
                  ` : ''}}
                </div>

                <!-- Defender -->
                <div class="agent-box">
                  <div class="agent-header defender-header">
                    <span>🛡️ Defender Agent</span>
                    <span style="font-size:11px; background:#f3e8ff; color:#6b21a8; padding:1px 6px; border-radius:4px;">
                      ${{l.defender.concede_charge ? 'Conceded' : 'Contest: ' + l.defender.alternative_class}}
                    </span>
                  </div>
                  <div><strong>Principle of Charity:</strong> ${{l.defender.charitable_interpretation}}</div>
                  ${{!l.defender.concede_charge && l.defender.counter_quote ? `<div class="quote-box">Counter-Quote: "${{l.defender.counter_quote}}"</div>` : ''}}
                  ${{l.defender.reasoning_content ? `
                    <details style="margin-top:6px;">
                      <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#475569;">🧠 Inner Thinking (raw_calls.jsonl)</summary>
                      <div style="background:#f8fafc; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #e2e8f0; margin-top:4px; font-family:monospace; color:#334155;">${{escapeHtml(l.defender.reasoning_content)}}</div>
                    </details>
                  ` : ''}}
                </div>

                <!-- Arbiter -->
                ${{!l.defender.concede_charge && l.arbiter.content ? `
                  <div class="agent-box" style="border-color:#fca5a5; background:#fffaf0;">
                    <div class="agent-header arbiter-header">
                      <span>⚖️ Dialectical Arbiter</span>
                      <span style="font-size:11px; background:#fee2e2; color:#991b1b; padding:1px 6px; border-radius:4px;">
                        Verdict: ${{l.arbiter.prediction}} (Conf: ${{l.arbiter.confidence}})
                      </span>
                    </div>
                    <div style="font-size:12px; line-height:1.4;">${{l.arbiter.content}}</div>
                    ${{l.arbiter.reasoning_content ? `
                      <details style="margin-top:6px;">
                        <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#991b1b;">🧠 Arbiter Chain-of-Thought (raw_calls.jsonl)</summary>
                        <div style="background:#fff5f5; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #fecaca; margin-top:4px; font-family:monospace; color:#7f1d1d;">${{escapeHtml(l.arbiter.reasoning_content)}}</div>
                      </details>
                    ` : ''}}
                  </div>
                ` : ''}}
              </div>

              <!-- GPT Column -->
              <div class="model-col">
                <div class="model-title">
                  <span>🤖 gpt-oss-120b</span>
                  <span class="badge ${{g.defender.concede_charge ? 'badge-conceded' : 'badge-contested'}}">
                    ${{g.defender.concede_charge ? 'Conceded (Fast-Path)' : 'Contested (Arbiter)'}}
                  </span>
                </div>

                <!-- Prosecutor -->
                <div class="agent-box">
                  <div class="agent-header prosecutor-header">
                    <span>⚡ Prosecutor Agent</span>
                    <span style="font-size:11px; background:#dbeafe; color:#1e40af; padding:1px 6px; border-radius:4px;">
                      Cand: ${{g.prosecutor.candidate_class}}
                    </span>
                  </div>
                  <div><strong>Mechanism:</strong> ${{g.prosecutor.defect_mechanism}}</div>
                  <div class="quote-box">Evidence Quote: "${{g.prosecutor.quote}}"</div>
                  ${{g.prosecutor.runner_up_class ? `<div style="margin-top:6px; font-size:11.5px; color:#64748b;">Runner-up: <strong>${{g.prosecutor.runner_up_class}}</strong> ("${{g.prosecutor.runner_up_quote}}")</div>` : ''}}
                  ${{g.prosecutor.reasoning_content ? `
                    <details style="margin-top:6px;">
                      <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#475569;">🧠 Inner Thinking (raw_calls.jsonl)</summary>
                      <div style="background:#f8fafc; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #e2e8f0; margin-top:4px; font-family:monospace; color:#334155;">${{escapeHtml(g.prosecutor.reasoning_content)}}</div>
                    </details>
                  ` : ''}}
                </div>

                <!-- Defender -->
                <div class="agent-box">
                  <div class="agent-header defender-header">
                    <span>🛡️ Defender Agent</span>
                    <span style="font-size:11px; background:#f3e8ff; color:#6b21a8; padding:1px 6px; border-radius:4px;">
                      ${{g.defender.concede_charge ? 'Conceded' : 'Contest: ' + g.defender.alternative_class}}
                    </span>
                  </div>
                  <div><strong>Principle of Charity:</strong> ${{g.defender.charitable_interpretation}}</div>
                  ${{!g.defender.concede_charge && g.defender.counter_quote ? `<div class="quote-box">Counter-Quote: "${{g.defender.counter_quote}}"</div>` : ''}}
                  ${{g.defender.reasoning_content ? `
                    <details style="margin-top:6px;">
                      <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#475569;">🧠 Inner Thinking (raw_calls.jsonl)</summary>
                      <div style="background:#f8fafc; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #e2e8f0; margin-top:4px; font-family:monospace; color:#334155;">${{escapeHtml(g.defender.reasoning_content)}}</div>
                    </details>
                  ` : ''}}
                </div>

                <!-- Arbiter -->
                ${{!g.defender.concede_charge && g.arbiter.content ? `
                  <div class="agent-box" style="border-color:#fca5a5; background:#fffaf0;">
                    <div class="agent-header arbiter-header">
                      <span>⚖️ Dialectical Arbiter</span>
                      <span style="font-size:11px; background:#fee2e2; color:#991b1b; padding:1px 6px; border-radius:4px;">
                        Verdict: ${{g.arbiter.prediction}} (Conf: ${{g.arbiter.confidence}})
                      </span>
                    </div>
                    <div style="font-size:12px; line-height:1.4;">${{g.arbiter.content}}</div>
                    ${{g.arbiter.reasoning_content ? `
                      <details style="margin-top:6px;">
                        <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#991b1b;">🧠 Arbiter Chain-of-Thought (raw_calls.jsonl)</summary>
                        <div style="background:#fff5f5; padding:8px 10px; border-radius:4px; font-size:11px; white-space:pre-wrap; max-height:180px; overflow-y:auto; border:1px solid #fecaca; margin-top:4px; font-family:monospace; color:#7f1d1d;">${{escapeHtml(g.arbiter.reasoning_content)}}</div>
                      </details>
                    ` : ''}}
                  </div>
                ` : ''}}
              </div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    function escapeHtml(text) {{
      if (!text) return '';
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }}

    // Initial render
    renderCurrentPage();
  </script>
</body>
</html>'''
    out_path.write_text(html_content, encoding='utf-8')

if __name__ == '__main__':
    main()
