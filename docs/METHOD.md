# Method

The system implements Conflict-Guided Multi-Agent Fallacy Reasoning for CoCoLoFa.

The analytical roles are three independent peer experts over the same raw input:
FORM (`structure`), FUNCTION (`goal`), and FAILURE (`counterargument`).
The conflict-guided interaction topology is the system design.

## Flow

1. `structure` independently instantiates fallacy-specific structural slots.
2. `goal` independently identifies the conclusion or goal and whether a cue does justificatory work.
3. `counterargument` independently states the strongest concise objection and exposed failure mode.
4. Candidate synthesis deterministically prunes role-specific non-viable hypotheses.
5. Targeted resolvers compare only surviving conflicting candidates.
6. `arbiter` adjudicates only surviving hypotheses; the engine maps a selected candidate to the benchmark task label.

The raw TARGET text is authoritative. TITLE and immediate parent are context only. Evidence spans must be substrings of TARGET.

## Trace

Per-sample traces are YAML files with sample metadata, input text, initial analysis, conflicts, arbiter output, and call/token/time stats. There is no post-hoc pretty trace.
# Expert Output Contract

At the model boundary, every stage selects evidence_ids from TARGET-only
passages of up to 30 words, with stable IDs and original character offsets.
The runtime restricts IDs to the supplied passages and resolves them back to
verbatim evidence_spans after generation/cache validation. Cached responses
contain IDs only; traces and downstream support contain the original text.
Passages are addressable text blocks, not inferred sentence boundaries.

Only Structure derives a candidate deterministically from structure_type and
instantiated slots. Goal proposes candidate or null with conclusion_or_goal,
supporting_reason, support_relation, and label_justification. Counterargument
proposes candidate or null with challenged_inference, decisive_counterargument,
and label_justification. No mechanism/failure enum determines their labels.

All explanations remain visible in traces, terminal reports, and survivor
support sent to resolver/arbiter. Viability flags screen proposals, not certify
their truth. Adjudication checks explanations against TARGET and the proposed
label; a structural form or a legitimate warning alone is not a fallacy.
Schema validation checks shape and required text, not semantic correctness.

The arbiter returns a single final selected_candidate (or null) and a
 decision_reason plus decisive_condition. verified and rejection_reason are
 derived by the engine for trace compatibility, never independently predicted.
