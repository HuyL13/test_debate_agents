import json

from src.io_utils import digest


SEMANTIC_SYSTEM_PROMPT = """You are extracting the latent reasoning structure of an argument.

Do NOT classify the fallacy.
Do NOT assign the comment to a predefined reasoning mode.
Do NOT perform mechanical entity replacement.

Read the complete target comment first. Understand the argument, then abstract
away topic-specific content while preserving the inferential structure.

Follow this order internally:

1. Identify the actual PREMISE.
2. Identify the actual CONCLUSION.
3. Identify the inferential bridge: WHY is the premise supposed to support the conclusion?
4. Determine the conclusion direction.
5. Only after steps 1-4, remove topic-specific content.
6. Write canonical_reasoning as a natural-language abstract inference.

Important rules:

- Preserve reasoning direction inside canonical_reasoning.
- Preserve whether historical persistence is treated as value, legitimacy,
  reliability, stability, entrenched harm, precedent, prediction, or another
  semantic relation.
- A long-standing SYSTEM may be treated as stable and deeply embedded, leading
  to resistance to abrupt replacement. A harmful PRACTICE may instead be
  treated as entrenched harm, leading to stronger intervention.
- Do not reduce the argument to keywords or a summary that loses the bridge.
- Do not replace every noun with an uppercase token. Prefer natural abstractions
  such as "a long-standing SYSTEM", "a harmful PRACTICE", "a GROUP", "an
  established NORM", or "a historical ACTION".
- Use only as much abstraction as necessary. The output must remain grammatical
  and semantically natural English.
- Do not include the conclusion inside the premise.
- Historical reference alone does not imply preservation.
- Opposite-direction arguments must remain clearly distinguishable.
- The canonical text must include a clear premise -> bridge -> conclusion
  progression, using prose and arrows only when they improve clarity.

Return strict JSON with exactly these fields and no others:

{
  "sample_id": "...",
  "original_text": "...",
  "canonical_reasoning": "..."
}

Copy sample_id exactly. Copy original_text exactly from the target comment.
canonical_reasoning must preserve the abstract premise, inferential bridge,
abstract conclusion, and direction. Never output a bare X or Y placeholder,
generic labels such as "comment", or a bag of uppercase tags.
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

