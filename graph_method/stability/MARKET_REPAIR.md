# Market GPT-OSS adapter repair

The old bulk snapshot had 46 contract-valid graphs out of832 completed samples,
including40 empty proposition lists. Twenty-four previously proposition-failed
samples were selected across eight labels and24distinct articles.

The fix uses plain generation with the exact output schema in the system prompt,
then the existing local validators. Native response_format decoding is disabled
for Market gpt-oss-120b. This is an empirically tested compatibility workaround,
not proof of a specific internal provider bug. All stages use the same Market
model; provider/output contract changes have separate cache identities.

Verification: paired old batch0/24complete; repaired source24/24, relations24/24,
warrant typing24/24; no empty graphs, no length finishes. Source-stage outputs
were reused from the first repaired run; warrant typing was retested after its
second fix. Three warrant responses needed narrow closing-brace normalization,
reported separately from raw first-pass contract validity. Original responses
remain in calls/. Two model quality repairs remain visible in stage metrics.

Additional safeguards:

- A nonempty source comment cannot be accepted as an empty proposition repair.
- Concession/adoption warrant=other is computed in code, not requested from LLM.
- JSON normalization only removes up to4extra closing braces after an already
  complete parsed object; no content is fabricated, two objects/prose/internal
  malformed JSON are rejected, and all semantic validators remain enabled.
- Bulk stops if contract validity is below80% across32completed samples; queued
  work is cancelled, in-flight results retained, incomplete metrics saved and
  exit code2 returned. This is an operational guard, not a semantic threshold.
- The launcher uses four workers and four request slots, independent Market
  pacing, a per-run lock, unbuffered console output and an append-only log.

Run100first from any PowerShell directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Downloads\graph_output_probe\stability\run_market_train.ps1" -Name market_gptoss_check100_r1 -Limit 100
```

Full TRAIN command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Downloads\graph_output_probe\stability\run_market_train.ps1" -Name full_train_market_gptoss120b_r1
```

This fixes output transport/parsing; it does not establish semantic correctness.
Manual source inspection still finds questionable projection/support directions.
Graphs remain drafts requiring the TRAIN review policy previously selected.

Evidence: market_repair_format_probe.json,
market_gptoss_repair_summary.json,
market_gptoss_repair_pilot_r2_report.html.
