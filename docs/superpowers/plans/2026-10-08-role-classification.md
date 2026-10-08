# Role-based classification refactor

Goal: make graph/role matching drive eight-label dataset classification, with legacy recovery unchanged and disabled during primary evaluation.

Architecture: preserve syntax spans and deterministic discourse links. One neutral extraction request, with at most one bounded conclusion-coverage completion, identifies argument families, grounded role quotes, stance and relation status. Code maps role-complete structures to fallacy templates, orders/deduplicates candidates and compares structural support. No mechanism/defect booleans or certainty claims are used as vetoes. An optional unresolved fallback uses the existing legacy pipeline; primary evaluation does not invoke it.

Constraints: no gold in prompts; no extra log artifacts; exact quotes; no API secrets; keep test regression diagnostic and use train/dev for evaluation. Direct baseline receives source text only. Implicit pair resolution is not invoked by the new primary path; extraction handles local relations; completion remains restricted to supplied graph spans.

Tasks:
1. Add tests for grounded role matching, missing sample rejection, ordered escalation, criticized reasoning, ambiguity and clean direct baseline.
2. Implement neutral role schemas, span-to-node mapping, deterministic pattern matching and comparative selection.
3. Connect default pipeline to role matching; preserve legacy recovery separately and expose primary-only evaluation.
4. Fix coverage/metrics to include unresolved samples and distinguish them from API errors.
5. Run tests, train/dev smoke and the four diagnostic samples; compare clean direct baseline; document results and limitations.

Implementation and small evaluation completed. Primary v3.2: 1/4 correct, 3 unresolved. Direct baseline: 2/4 correct. Relation ablation: 1/4 correct, 3 unresolved. Dev smoke: 0/4 resolved. Train smoke: 1/2 correct, 1 unresolved. No improvement or graph contribution established. Role extraction remains the main bottleneck; unresolved is a diagnostic outcome, not a ninth dataset label.

Revision 4.5: require family attributes in the output schema; validate distinct complete roles; use article-excluded train demonstrations; preserve criticism/reporting; suppress metadiscourse event endpoints; cover postposed reasons and relevant existing argument backbones within an eight-node completion subgraph; retain primary results when optional completion is invalid. Failed completion is explicit in the report. Automatic causal-to-priority projection and its unused impact attribute were removed after a negative-case review. Recovery internals remain unchanged and primary recovery is disabled.

The user permits leaving diagnostic sample 599:7794 unsolved when its Worse Problems structure is atypical. It remains in regression_four.json with its original gold. regression_supported_three.json is a transparent separate subset excluding that sample, not a modification of test labels. An inspection of 12 train Worse Problems comments from distinct articles found expressed comparison/focus shifts; this is a qualitative outlier check, not proof that the annotation is incorrect. The eight additional validation samples remain a separate smoke check, not a benchmark or a guarantee.

Graph-driven coverage auditing now also checks unrepresented neutral discourse anchors. Event audits exclude transition/advice endpoints; already represented ordinary forecasts do not trigger another extraction. Optional completion preserves primary extraction under validation, rate-limit and provider failures, recording a separate failure count.

Verified v4.5 supported regression: 3/3 correct, each with appropriate exact evidence; 0 unresolved, errors or recovery; 3 total extraction requests. The prior v4.4 supported run also achieved 3/3. Fresh full code checks: 253 tests passed. Independent v4.3 validation-eight smoke: 3 correct, 2 wrong, 3 unresolved, no errors. This demonstrates remaining role-attribute semantic failures; no broad accuracy or graph contribution claim is justified. The revised scope is the three supported diagnostic samples, with the original outlier retained unchanged in the full report.
