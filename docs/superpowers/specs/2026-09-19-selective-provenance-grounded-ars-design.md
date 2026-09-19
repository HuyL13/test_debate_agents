# Selective Provenance-Grounded ARS Design

**Date:** 2026-09-19

**Status:** Approved design, pending implementation plan

## Objective

Turn the existing ARS research prototype into a reliable and efficient experimental system for a full NLP paper within three months. The proposed method, Selective Provenance-Grounded ARS (SPG-ARS), preserves label isolation, grounds intermediate reasoning in immutable source spans, and invokes role-preserving review only when deterministic structural conflicts justify the additional cost.

The system must support defensible comparisons among single-agent, legacy diagnostic, always-review ARS, and selective-review ARS methods while recording complete coverage, inference failures, latency, token usage, retries, and model versions.

## Research Positioning

Acceptability, Relevance, and Sufficiency are established argument-quality dimensions. Role-specific multi-agent deliberation and adaptive protocols also exist in prior work. The intended contribution is therefore not the existence of ARS dimensions or multi-agent debate in isolation.

The proposed contribution is their operational combination for logical-fallacy detection and classification:

1. Label knowledge is isolated from decomposition and specialist analysis.
2. Intermediate evidence is linked to deterministic source spans instead of regenerated quotations.
3. Review is triggered by structural conflict rather than gold labels, vote counts, or self-reported confidence.
4. The evaluation measures predictive quality, reliability, and cost on identical paired samples.

The primary paper claim is:

> Selective provenance-grounded ARS improves the reliability and cost-effectiveness of multi-agent logical-fallacy analysis by isolating label knowledge, grounding intermediate reasoning in immutable source spans, and invoking deliberation only under structural disagreement.

If predictive performance does not improve, the system still supports a valid negative-result claim about when multi-agent deliberation regresses or adds cost without benefit.

## Research Questions

- **RQ1:** Do theory-grounded ARS roles outperform generic Inference, Evidence, and SemanticContext roles under the same model and context?
- **RQ2:** Does selective role-preserving review retain the quality of always-review ARS while reducing calls, tokens, and latency?
- **RQ3:** Does immutable span grounding reduce invalid responses, retries, and unsupported evidence compared with generated quotations?
- **RQ4:** Under which samples and fallacy classes does deliberation change a correct prediction to an incorrect one, or vice versa?

## Scope

### In scope

- CoCoLoFa detection and eight-class classification.
- Existing single, diagnostic no-debate, diagnostic review, ARS no-debate, and ARS review baselines.
- A new `ars_selective_review` policy.
- Deterministic text-span indexing and span-reference validation.
- Fixed stratified development selections.
- Deterministic sharding and validated shard merging.
- Paired statistical analysis, cost/reliability reporting, and qualitative trace analysis.
- Human evaluation of intermediate reasoning if the paper claims interpretability or explanation quality.

### Out of scope

- Reinforcement learning, retrieval, external fact checking, tool use, and cross-sample memory.
- Silent correction of model predictions or silent replacement of failed samples.
- Model selection using test results.
- Claiming full PARD reproduction.
- Claiming that schema validity proves semantic correctness.

## System Architecture

```text
ModelInput
  -> deterministic source-span indexer
  -> label-agnostic argument decomposer using span IDs
  -> independent Acceptability / Relevance / Sufficiency specialists
  -> deterministic conflict gate
       -> no conflict: final ARS arbiter
       -> conflict: synchronous role-preserving review -> final ARS arbiter
  -> prediction, trace, usage, reliability events
```

Only the final ARS arbiter receives the CoCoLoFa label ontology. The decomposer, specialists, conflict gate, and review stage remain label-agnostic.

## Immutable Source Spans

Before the first model call, the runner converts the allowlisted context into ordered immutable spans. Each span contains:

- `span_id`: deterministic within the sample and source;
- `source`: `title`, `article`, `parent_comment`, or `target_comment`;
- `text`: exact source substring;
- `start` and `end`: character offsets in the original source string.

The initial implementation uses deterministic sentence-like segmentation with a fallback that preserves the entire nonempty source as one span. It must not paraphrase, normalize spelling, or rewrite punctuation.

The decomposer selects span IDs and may assign argumentative roles, modality, and inference links. Specialists cite target-comment span IDs. Validators resolve each ID back to the immutable source and reject unknown IDs or citations from a disallowed source. Generated explanatory fields remain label-agnostic and schema-validated.

This replaces fragile exact-substring generation while retaining stronger provenance: evidence is copied by code from the source rather than trusted from model output.

## Selective Review Policy

All SPG-ARS samples execute:

1. one argument-decomposition call;
2. three independent specialist calls;
3. deterministic conflict detection;
4. either zero or three review calls;
5. one final arbiter call.

Therefore, valid samples require five logical calls without review and eight logical calls with review, excluding retries.

Review is triggered when at least one of these conditions holds:

- specialists disagree between `satisfied` and `violated` on decisive dimensions;
- a specialist marks the decomposition `incorrect` or `partially_correct`;
- referenced premise or conclusion IDs are inconsistent with the decomposition;
- a required target evidence span is missing or invalid;
- the set of specialist findings cannot establish a consistent argument-quality reading.

Review is not triggered by gold labels, majority vote, previous samples, provider cost, or self-reported confidence. The gate produces explicit machine-readable reasons in the trace.

Each review call receives the same immutable initial diagnoses and no earlier review output. Each reviewer remains inside its original ARS dimension. The arbiter receives only raw input, decomposition, final diagnoses, span table, and gate decision.

## Benchmark Selection

`--limit N` remains a plumbing convenience and must not define paper subsets because it selects a dataset prefix.

Paper pilots use a versioned selection manifest containing explicit sample IDs. The selector is deterministic and stratified as follows:

- classification: stratify by all eight labels and article;
- detection: stratify by binary label and article;
- prevent duplicate IDs;
- record the eligible population, selected IDs, selection seed, and algorithm version;
- never read model predictions during selection.

The same selection manifest is reused across all compared methods and repeated runs.

## Experimental Matrix

Development ablations use:

| ID | Method |
|---|---|
| A | single |
| B | diagnostic_no_debate |
| C | diagnostic_review |
| D | ars_no_debate |
| E | ars_review |
| F | ars_selective_review |

All methods in a comparison use the same model, provider, context, temperature, completion budget, sample IDs, and task definition. Each stochastic repetition uses a fresh cache directory. Copying an existing cache is not an independent repetition.

The final test evaluates single, the strongest non-ARS baseline, and the frozen selected ARS method. Full test coverage is 798 detection samples and 481 classification samples. No score is published for incomplete coverage.

## Metrics and Statistical Analysis

### Predictive metrics

- Detection: accuracy, positive-class precision, recall, F1, false-positive count/rate, and false-negative count/rate.
- Classification: accuracy, macro precision/recall/F1 across eight labels, per-class F1, and confusion matrix.

### Reliability and efficiency

- logical calls and provider attempts per sample;
- prompt, completion, total, and cached tokens;
- end-to-end latency and provider latency;
- validation failures by stage and reason;
- timeout and transport failure counts;
- reviewed-sample rate and conflict-reason distribution;
- complete coverage rate.

### Paired analysis

- paired bootstrap confidence intervals for metric differences;
- McNemar testing for paired correctness changes;
- `wrong_to_correct`, `correct_to_wrong`, and net review gain;
- cost-quality Pareto comparison;
- results across at least three independent repetitions when temperature is above zero.

Statistical tests supplement effect sizes and confidence intervals; they do not replace them.

## Scalability and Sharding

The current per-sample execution is serial and one output directory permits only one writer. Scaling uses deterministic process-level sharding rather than concurrent writes to a shared run:

- each shard receives a disjoint deterministic subset of the shared selection manifest;
- each shard has its own output directory, audit log, and cache database;
- shard manifests include the parent experiment fingerprint and shard coordinates;
- a merge command verifies identical experiment identity, disjoint IDs, expected full coverage, and trace validity;
- merged predictions follow the original selection order;
- incomplete or conflicting shards prevent scoring.

This design permits bounded parallel execution without weakening cache, audit, or resume guarantees.

## Failure Handling

The default research run records a failed sample and continues until a configurable failure threshold is reached. Failed rows never contribute to metrics, and any failed or missing sample keeps the overall result `incomplete` with `metrics: null`.

Resume retries only missing or failed samples under the identical fingerprint. Provider failures, schema failures, provenance failures, and semantic-validator failures remain separately classified. No fallback invents a prediction.

## Human Evaluation

If the paper claims interpretability or explanation quality, two annotators independently review a balanced sample of approximately 100 traces. They assess:

- decomposition fidelity to the source;
- correct premise/conclusion linkage;
- specialist adherence to its assigned ARS dimension;
- whether cited evidence supports the finding;
- usefulness of the final explanation.

The paper reports the annotation instructions, agreement statistic, disagreements, and adjudication process. Human evaluation is omitted only if all interpretability claims are removed.

## Reproducibility Contract

Every reported run records:

- source, config, prompt/schema, and dataset hashes;
- explicit selection manifest;
- provider and returned model identifier;
- execution timestamps and environment versions;
- output coverage, retry events, token usage, and latency;
- whether results are live, cached, or synthetic.

Prompts and configurations are frozen before final test. Reports are regenerated from validated artifacts rather than manually copied values. API credentials remain environment-only and must not appear in configs, logs, reports, or commits.

## Success Criteria

The system is paper-ready when all of the following hold:

1. The complete automated suite passes and includes SPG-ARS, span provenance, selection, sharding, merge, and statistical-analysis tests.
2. ARS invalid-output rate is below 1% after configured retries on the frozen full-development run.
3. Every reported result has complete validated coverage.
4. The selected method either improves the primary metric with paired evidence or stays within one absolute F1 point while reducing total tokens by at least 30% relative to always-review ARS.
5. Single-agent and strongest existing baseline use identical paired samples and model conditions.
6. Final test configuration is frozen before inference and is not modified from test outcomes.
7. Interpretability claims, if retained, are supported by the specified human evaluation.

## Twelve-Week Delivery Sequence

- **Weeks 1–2:** systematic related-work review, research-question freeze, selection protocol, and external-dataset decision.
- **Weeks 3–4:** immutable span grounding, ARS schema/prompt migration, selective conflict gate, and failure-continuation policy.
- **Week 5:** deterministic sharding, validated merge, and run-status reporting.
- **Week 6:** benchmark orchestration, paired statistics, and report generation.
- **Weeks 7–8:** stratified development pilot, independent repetitions, error analysis, and dev-only revisions.
- **Week 9:** frozen full-development matrix and finalist selection.
- **Week 10:** frozen full-test evaluation and optional external-dataset evaluation.
- **Week 11:** qualitative trace study, human evaluation, and statistical synthesis.
- **Week 12:** paper writing, artifact cleanup, reproducibility verification, and release packaging.

## Principal Risks

- **Novelty overlap:** mitigate with a systematic related-work table before implementation claims are finalized.
- **Provider instability or model drift:** record returned model identifiers and dates; maintain a second validated provider only as a robustness check, not as an untracked substitution.
- **Runtime remains excessive:** use process-level sharding and eliminate unconditional review before expanding the experimental matrix.
- **Selective gate misses unanimously wrong analyses:** report this limitation and compare against always-review ARS on identical samples.
- **Public test exposure from prior experiments:** pre-register the new frozen protocol and add an external or newly held-out evaluation where feasible.
- **Valid spans support incorrect reasoning:** retain semantic error analysis and human evaluation; do not equate provenance validity with correctness.
