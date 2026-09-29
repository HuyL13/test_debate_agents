import json

from src.io_utils import digest


SEMANTIC_SYSTEM_PROMPT = """You are given an argumentative comment.

Your task is to rewrite the comment into a topic-independent canonical reasoning representation.

The goal is NOT to summarize the comment and NOT to classify its fallacy.

The goal is to preserve the argument's inferential structure while removing unnecessary topic-specific content.

## What CANONICAL_REASONING must preserve

Before rewriting, internally determine:

1. What is the main premise or evidence?
2. What conclusion is the author trying to support?
3. Why is the premise supposed to support that conclusion?
4. What is the direction of the inference?
   - preserve something
   - continue something
   - resist change
   - restore something
   - accept something
   - reject something
   - change or remove something
   - avoid something
   - or merely predict or describe something

The final canonical reasoning must preserve these relations.

## Detopicalization

Remove details that are specific to the topic, such as:

- specific countries
- politicians
- organizations
- religions
- ethnic or social groups
- named policies
- websites
- technologies
- products
- events
- specific institutions

Replace them only when needed with simple semantic descriptions such as:

- a GROUP
- an AUTHORITY
- a SYSTEM
- a PRACTICE
- a NORM
- a ROLE
- an ACTION
- a METHOD
- an INSTITUTION
- an OUTCOME

However:

Do NOT mechanically replace every noun with an uppercase placeholder.

The result must remain fluent natural language.

Bad:

POWER_HOLDING_GROUP follows POLICY because TRADITIONAL_NORM supports SYSTEM.

Good:

A SYSTEM has existed for a long time and is deeply embedded in a society, so its persistence is treated as evidence that replacing it abruptly would be risky.

## Preserve the inferential bridge

Do not produce a generic summary such as:

A long-standing practice should continue.

Instead preserve WHY the premise supports the conclusion.

Good:

A SYSTEM has existed for a long time and maintained stability -> its longevity is treated as evidence of reliability -> resist replacing the SYSTEM.

Another example:

A harmful PRACTICE has persisted for a long time -> its persistence indicates that the problem is entrenched rather than legitimate -> stronger intervention is needed to overcome the PRACTICE.

These two arguments must remain clearly different even though both mention something long-standing.

## Important constraints

- Understand the argument BEFORE abstracting it.
- Do not classify the argument into a predefined reasoning mode.
- Do not mention the fallacy label.
- Do not use keyword matching.
- Do not assume that mentioning history or tradition means the conclusion supports preservation.
- Preserve opposite reasoning directions.
- Remove topic content only when it is not necessary for the logical relation.
- Keep distinctions such as successful past experience vs harmful past experience;
  longevity as evidence of reliability vs longevity as evidence of entrenched harm;
  preservation vs removal; continuation vs avoidance; and normative recommendation
  vs descriptive prediction.
- Do not add reasoning that is absent from the original comment.
- Do not copy unnecessary wording from the original comment.
- The result should normally be one concise natural-language sentence or inference chain.
- Prefer the form ABSTRACT PREMISE -> INFERENTIAL BRIDGE -> ABSTRACT CONCLUSION,
  but ordinary natural-language sentences are acceptable if the relation is equally clear.

## Example

Original:

Rulers concealing information from those they rule is basically tradition at this point. Laws and enforcement mechanisms need to be far stronger to overcome the timeless practice of corruption.

Good canonical reasoning:

A harmful practice has persisted for a long time because those responsible avoid accountability -> its persistence indicates an entrenched problem rather than legitimacy -> stronger intervention is needed to overcome the practice.

Bad canonical reasoning:

A governing authority traditionally withholds information, so stronger laws are needed.

Why bad: it retains too much topic content and does not explicitly preserve the important inferential relation between persistence, entrenched harm, and the need for change.

## Output

Return STRICT JSON only:

{
  "sample_id": "<provided sample id>",
  "original_text": "<original text unchanged>",
  "canonical_reasoning": "<detopicalized natural-language reasoning>"
}

Do not output explanations, markdown, or additional fields.
Copy sample_id exactly and copy original_text unchanged.
"""


def semantic_extraction_prompt(sample, use_parent_context=False):
    payload = {
        "stage": "semantic_extraction",
        "sample_id": sample["sample_id"],
        "input": {"target": sample["comment"]},
    }
    if use_parent_context:
        payload["input"]["parent_comment"] = sample.get("parent_comment", "")
    return SEMANTIC_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False)


def semantic_prompt_hash():
    return digest(SEMANTIC_SYSTEM_PROMPT)


def cluster_audit_prompt(cluster):
    system = """Describe what this cluster appears to represent. Do not name a mode from keywords alone. Infer the shared premise, conclusion, bridge, variation, and outliers from the supplied members. Return strict JSON."""
    return system, json.dumps({"stage": "cluster_audit", "cluster": cluster}, ensure_ascii=False)


def cluster_mode_prompt(audit, members=None):
    system = """Induce one reasoning mode from this audited cluster. Use only the supplied evidence. Return strict JSON with premise pattern, conclusion pattern, invariant bridge, non-invariants, boundaries, and supporting member IDs."""
    return system, json.dumps({"stage": "cluster_mode_induction", "cluster_audit": audit, "members": members or []}, ensure_ascii=False)


def merge_prompt(modes):
    system = """Conservatively compare audited cluster modes. Merge only genuinely identical inferential relations. Keep separate modes with different direction, evidence, or bridge. Return strict JSON."""
    return system, json.dumps({"stage": "mode_merge", "modes": modes}, ensure_ascii=False)


FINAL_DEFINITION_SYSTEM_PROMPT = """Induce a definition only from audited reasoning modes. Do not add textbook knowledge or unsupported modes. Cite the supplied cluster and member IDs through the discovered mode records. Keep noisy or dataset-edge patterns separate from the core invariant. Return strict JSON."""


def final_definition_prompt(label, modes, merge_plan):
    return FINAL_DEFINITION_SYSTEM_PROMPT, json.dumps({"stage": "final_definition", "label": label,
                                                        "audited_modes": modes, "merge_plan": merge_plan}, ensure_ascii=False)


def cluster_prompt_hashes():
    return {"cluster_induction_prompt_sha256": digest("cluster audit and mode induction prompts"),
            "final_induction_prompt_sha256": digest(FINAL_DEFINITION_SYSTEM_PROMPT)}

