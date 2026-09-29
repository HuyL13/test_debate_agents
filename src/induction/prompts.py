import json

from src.io_utils import digest


SEMANTIC_SYSTEM_PROMPT = """You extract latent inferential structure from an argument.
Do not classify the argument and do not assign it to a predefined reasoning subtype.
Read the complete target comment before abstracting it.

First identify premises, then the conclusion, then the inferential bridge, then
direction and polarity. Only after that remove topic-specific content. Preserve
opposite conclusions as opposite directions. Return strict JSON matching the
provided schema. CANONICAL_REASONING must be grammatical prose, not a bag of tags.
Do not treat words such as tradition, historical, always, expert, majority, or
natural as sufficient evidence for a relation. If a field is not applicable,
return null rather than inventing content.
"""


def semantic_extraction_prompt(sample, use_parent_context=False):
    payload = {
        "stage": "semantic_extraction",
        "sample_id": sample["sample_id"],
        "article_id": sample["article_id"],
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

