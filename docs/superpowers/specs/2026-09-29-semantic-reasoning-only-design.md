# Semantic Reasoning-Only Record Contract

## Goal

Replace the verbose semantic extraction record with a minimal, natural-language
representation for audit and sentence embedding. The model must preserve the
premise-to-bridge-to-conclusion relation inside `canonical_reasoning` while
removing topic-specific content.

## Final record contract

Every successful semantic record contains exactly these fields:

```json
{
  "sample_id": "article_id:comment_id",
  "original_text": "the complete target comment",
  "canonical_reasoning": "natural-language abstract premise → bridge → conclusion"
}
```

`premise`, `conclusion`, `direction`, `ambiguity_notes`, `article_id`,
`comment_id`, `bridge`, `inference_source`, `inference_target`,
`evidential_basis`, `premise_valence`, `relation_polarity`, and all other
semantic helper fields are removed from the persisted semantic record. The
direction must remain explicit in the natural-language canonical reasoning, but
is not emitted as a separate field.

## Extraction rules

The prompt requires the model to read the complete comment, identify the real
premise, conclusion, inferential bridge, and direction internally, then perform
detopicalization. It must not classify into predefined modes or mechanically
replace every noun with an uppercase token.

Natural abstractions such as `a SYSTEM`, `a GROUP`, `a PRACTICE`, `a ROLE`, and
`an established NORM` are preferred. Specific entities and topics are removed
only when the reasoning remains grammatical. The canonical text must preserve
whether persistence is interpreted as legitimacy/stability or entrenched harm,
and must distinguish preserve/continue reasoning from change/remove reasoning.

Production prompts must not include the named hard-case IDs as few-shot examples.
Those cases are reserved for post-run audit.

## Validation and resume

The schema rejects extra fields, empty or very short canonical text, copied
topic-specific names, keyword-only or tag-only representations, excessive
underscore-style uppercase placeholders, and duplicate `sample_id` records.
Resume and failure compaction key records by `sample_id`. Existing verbose
records are stale artifacts and are not semantically migrated; a subsequent
resume run drops them and requests fresh minimal records from the configured
LLM.

## Downstream behavior

Sentence embedding consumes only `canonical_reasoning`. Semantic audit checks
record completeness, copied text, topic leakage, canonical quality, hard-case
presence, and representation collapse. Clustering no longer computes purity
from removed semantic fields; direction is audited from canonical text and
cluster member review rather than injected as an embedding feature.

## Non-goals

- No external API execution is part of this code change.
- No automatic semantic rewriting of old records is attempted.
- No new fallacy mode taxonomy is introduced before clustering.
