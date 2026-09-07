# Adaptive disagreement review

The user stopped the full-test adaptive runs because the previous method was too
slow and dev quality lagged single inference. No partial test labels or accuracy
were used to design this revision. Original checkpoints and raw logs are retained.

The original planner policy remains available. New configs explicitly select
`engine.adaptive_policy: disagreement`:

- Three independent initial assessments are retained.
- If all labels agree, skip planning and deliberation; the arbiter still checks
  the original text and may disagree. Four logical calls per sample.
- If labels disagree, each role reviews exactly the same immutable initial
  reports, with no other revisions or history visible. One review per role,
  followed by the arbiter: seven logical calls, excluding retries.
- Each review must include a nonempty verbatim span from the target comment.
  Whitespace is normalized for validation. This enforces textual fidelity, not
  semantic correctness; an authentic quotation can still support a wrong analysis.
- Routing does not use self-reported confidence, gold labels, previous samples,
  learned rewards, or a paid planner. It can miss unanimously wrong interpretations.

This is a separate policy experiment, not a full PARD reproduction. The protocol
trace names this branch `independent_review`. `max_rounds` and `early_stop` still
control the legacy protocols; disagreement review always performs at most one
round and skips it on unanimous initial labels. It reduces calls by construction;
accuracy improvement must be measured, not assumed.

Run the dedicated `configs/*.review.yaml` on dev. Do not resume stopped adaptive
test runs with this source or combine predictions from the two policies. A later
test evaluation needs a new freeze and an entirely separate output directory.

The two running single baselines retain their already loaded original runtime.
For a future resume, the exact old Python source and absolute-path configs were
saved under `outputs/full-test-v1/frozen-runtime`. Run the original `.venv` Python
from that directory, using the original absolute freeze/output paths; current
source is intentionally incompatible with those old freezes.
