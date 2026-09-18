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
6. For detection, an empty survivor set maps to `Non-Fallacious`. For classification,
   the task is forced-choice: if viability pruning leaves no survivors, a dedicated
   recovery adjudicator first reconsiders labels proposed before pruning and, when
   all experts abstained, selects from the full eight-label space.
7. `arbiter` adjudicates only surviving hypotheses; classification arbiters must
   select exactly one allowed label, while detection arbiters may reject all survivors.

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


## Classification forced-choice recovery

CoCoLoFa classification is evaluated only on gold-positive examples and requires
one of the eight fallacy labels. Expert abstention remains allowed internally so
FORM/FUNCTION/FAILURE analyses are not forced to fabricate evidence. However,
an empty post-viability candidate set is not a valid terminal classification
state.

Recovery is explicit and auditable in `candidate_state.recovery`:

- `proposed_candidates`: use labels proposed by at least one expert before
  viability pruning, including proposals whose role-specific gate failed.
- `full_label_space`: when all experts abstain, choose from all eight labels.

The recovery adjudicator never receives gold annotations. RAW TARGET remains
authoritative, and the selected label must satisfy the same structural and
reasoning-defect checks used elsewhere.
