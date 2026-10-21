# Directed role core matching

## Multi-resolution bank

`build_multires_patterns.py` now builds a separate automatic/silver bank using
both `strict` and `core` motifs for every label. Each resolution receives the
same support, purity, bootstrap and per-label candidate limits. Strict motifs
retain the four facets in their identity; core motifs use their soft profiles.
This keeps discriminative detailed motifs without forcing fragmented sources
to agree on every facet. It does not manufacture a pattern for a missing label.

Every retained witness is re-canonicalized against its actual source graph.
Retrieval handles each pattern's resolution and deduplicates the same source
application within a label across the two resolutions. A label can still have
several distinct candidate applications. Use the new bank with the updated
matcher; no changes to source graphs are made. Eight supported TRAIN labels
alone do not establish independent recall or classification accuracy.

Policy `directed-role-core-soft-facets-r1` applies equally to all labels.

Canonical motif identity retains premise/target direction, relation kind,
scheme, author stance, scope change, alternative-set state, role incidence,
owner and explicit/implicit status. It preserves proposition multiplicity and
application-target dependencies. No separate source paths are unioned.

Modality, logical polarity, speech act and event role remain unchanged on source
graphs. They are stored in each witness's `attribute_profile`, rather than used
as hard identity colors. Retrieval reports a source profile and the best mean
attribute agreement over the pattern's witnesses. Its ranking score is
`pattern_quality * (0.9 + 0.1 * soft_attribute_score)`. This mild ranking factor
is an implementation choice, not an empirically optimized weight. A polarity
disagreement does not hard-reject retrieval; final verification still sees the
literal source and full source graph and must assess negation and modality.

Mining keeps the original thresholds: at least 5 distinct positive articles,
purity at least 0.45, 30 article-resampling rounds, recovery at least 0.8.
Purity's denominator includes competing label/article pairs. These quantities
measure structural support and resampling recovery, not semantic correctness.

The new bank must be used with the new matcher; older strict-signature banks
remain separate historical results. No graph extraction or API calls are needed
to rebuild this bank. Whole-TRAIN induction does not establish held-out recall.

Run:

```powershell
.\.venv-syntax\Scripts\python.exe -u experiment_v2.py --graphs full_train_span_fixed_r1_graphs.json --name full_train_silver_core_patterns_r1 --no-verify
```
