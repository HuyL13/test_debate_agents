# Adaptive disagreement review: dev10 results

Both runs completed; no test labels or partial test scores were used to revise the method.

| Task | Metric | Prior adaptive | Disagreement review | Single v3 |
|---|---|---:|---:|---:|
| detection | accuracy | 0.700 | 0.800 | 0.900 |
| detection | f1 | 0.571 | 0.667 | 0.800 |
| classification | accuracy | 0.700 | 0.800 | 0.800 |
| classification | macro_f1 | 0.444 | 0.475 | 0.486 |

The new policy is cheaper and improves over the immediately preceding adaptive runs, but does not beat the single reference: detection accuracy is lower, and classification macro-F1 is slightly lower at equal accuracy. It is a candidate, not a validated replacement for single.

Same ten dev samples previously inspected; temperature 1, one run, classification covers only five of eight labels. No claim of held-out generalization or statistical significance. Quotes enforce textual presence, not correctness. No adaptive full-test restart was performed.

64 automated tests passed. Validated full dev10 coverage and identical sample selections against both references. The two stopped full-test adaptive checkpoints are retained; single processes continue with their original runtime. The monitor only observes; it never restarts adaptive.

## detection

API attempts: 104 -> 50 (including retries). Tokens: 175,946 -> 66,011; reduction 62.5%.

Stop reasons: {'initial_consensus': 7, 'one_review_round': 3}. Invalid quote attempts: 1; all recovered.

[Complete per-attempt trace](traces/nvidia-detection-review-dev10-v1.md)

- `237:5508`: Fallacious -> Non-Fallacious; gold: Non-Fallacious.

## classification

API attempts: 115 -> 49 (including retries). Tokens: 208,870 -> 71,494; reduction 65.8%.

Stop reasons: {'initial_consensus': 8, 'one_review_round': 2}. Invalid quote attempts: 3; all recovered.

[Complete per-attempt trace](traces/nvidia-classification-review-dev10-v1.md)

- `237:10009`: Hasty Generalization -> Slippery Slope; gold: Slippery Slope.
- `226:5476`: Hasty Generalization -> False Dilemma; gold: Appeal to Majority.
