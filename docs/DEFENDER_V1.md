# Defender diagnostic v1

Only classification Defender prompt/instructions and its output validation change. Prosecutor and Arbiter prompts, schemas, calls, and adjudication policy remain unchanged. Detection is unchanged.

Defender reconstructs premise/conclusion, checks candidate conditions, compares runner-up under the same standard, and considers a third class only if both are weak. No extra independent LLM call is added.

Grounded shared quotes and missing regex cues no longer force concession. Short quotes are advisory. Invalid labels or missing/non-target evidence still raise validation errors for the existing retry mechanism. Same-label alternatives normalize to agreement without rewriting the explanation.

Prediction traces include `defender.raw_report` (submitted report before this normalizer) and `defender.validation` (`policy`, `normalization_reason`, `cue_found`, `shared_quote`, `warnings`). Provider response text remains in `raw_calls.jsonl`; schema validation may normalize enum spellings before `raw_report` is captured.

## Run

```bash
python -m src.run_classification --config configs/classification.adversarial.defender-v1.marketplace.yaml --limit 10
python -m src.run_classification --config configs/classification.adversarial.defender-v1.marketplace.yaml
python -m src.run_classification --config configs/classification.adversarial.defender-v1.gptoss120b.marketplace.yaml
```

Configs default to dev and new output directories. Use a different `--output` for each subset/full run; do not resume a 10-sample run as a full run. For test:

```bash
python -m src.run_classification --config configs/classification.adversarial.defender-v1.marketplace.yaml --split test --output outputs/defender-v1-llama70b-test
```

This is the combined prompt + validator revision, not an isolated validator ablation. Older configs also use the revised code. Existing output artifacts are not modified. Keeping Prosecutor code unchanged does not freeze its responses: the cache includes experiment identity and temperature remains 0.6. For a strict paired comparison, replay saved Prosecutor reports in a separate experiment. No accuracy improvement is established by offline tests.
