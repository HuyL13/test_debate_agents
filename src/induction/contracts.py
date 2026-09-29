import re

from src.schemas import validate_output


_GENERIC_TERMS = {
    "a", "an", "and", "argument", "because", "benefit", "belief", "bridge", "can", "case",
    "change", "claim", "conclusion", "continue", "continued", "continuity", "custom", "descriptive",
    "evidence", "example", "existing", "factor", "far", "for", "from", "future", "good", "harm",
    "held", "historical", "history", "idea", "imply", "indicate", "inference", "inferential", "instance",
    "intervention", "long", "maintain", "may", "method", "modern", "necessary", "need", "needed", "norm",
    "old", "outcome", "overcome", "past", "people", "practice", "premise", "preserve", "reason", "reasoning",
    "relation", "remove", "replace", "require", "requires", "resistance", "result", "restore", "strong",
    "stronger", "support", "supported", "system", "the", "therefore", "this", "timeless", "tradition",
    "traditional", "value", "valuable", "when", "while", "willingly", "works", "worked", "x", "y",
    "accountability", "accountable", "absence", "adverse", "beneficial", "conceal", "concealment", "deficient",
    "enduring", "enforcement", "entrenched", "group", "harmful", "legitimacy", "legitimate", "lack",
    "persistence", "persistent", "power", "problem", "responsible", "standing", "strengthen", "strengthened",
    "time", "long-standing", "longstanding",
}

_GENERIC_CAPITALIZED = {
    "A", "An", "Although", "As", "Because", "Even", "For", "From", "Given", "If", "It", "Long", "No", "One",
    "Past", "Since", "Some", "That", "The", "This", "When", "While",
}


def _string(max_length=2000):
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def semantic_schema():
    return {
        "type": "object",
        "properties": {
            "sample_id": _string(200),
            "original_text": _string(10000),
            "canonical_reasoning": {
                **_string(2000),
                "description": "Natural-language abstract reasoning that preserves premise, bridge, conclusion, and direction.",
            },
        },
        "required": ["sample_id", "original_text", "canonical_reasoning"],
        "additionalProperties": False,
    }


def validate_semantic_record(record, sample):
    validate_output(record, semantic_schema())
    if record["sample_id"] != sample["sample_id"]:
        raise ValueError("semantic record ID does not match sample")
    if record["original_text"] != sample["comment"]:
        raise ValueError("original_text must preserve the target comment")
    leakage = _topic_leakage_terms(record["original_text"], record["canonical_reasoning"])
    if leakage:
        raise ValueError("topic leakage in canonical_reasoning: " + ", ".join(sorted(leakage)))
    _validate_canonical_reasoning(record["canonical_reasoning"])
    return record


def _validate_canonical_reasoning(value):
    text = value.strip()
    if not text:
        raise ValueError("canonical_reasoning must be non-empty")
    if len(text.split()) < 8:
        raise ValueError("canonical_reasoning is too short to preserve inference")
    if re.search(r"(?<![A-Za-z])(?:X|Y)(?![A-Za-z])", text):
        raise ValueError("role-specific placeholders required; do not use bare X or Y")
    placeholders = set(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", text))
    if len(placeholders) > 2:
        raise ValueError("canonical_reasoning uses too many uppercase placeholders")
    if "+" in text or not re.search(r"[a-z]{2,}", text):
        raise ValueError("canonical_reasoning must be natural-language prose, not a keyword template")
    bridge_markers = (
        "because", "therefore", "so ", "leads", "treated as", "indicates", "supports",
        "justif", "requires", "needed", "rather than", "results", "means", "->", "→",
    )
    if not any(marker in text.casefold() for marker in bridge_markers):
        raise ValueError("canonical_reasoning must preserve an inferential bridge")


def _normalize_text(value):
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _topic_leakage_terms(original, canonical):
    canonical_proper_nouns = {
        token for token in re.findall(r"\b[A-Z][a-z]{2,}\b", canonical)
        if token not in _GENERIC_CAPITALIZED
    }
    source_proper_nouns = {
        token for token in re.findall(r"\b[A-Z][a-z]{2,}\b", original)
        if token not in _GENERIC_CAPITALIZED
    }
    proper_nouns = source_proper_nouns & canonical_proper_nouns
    source_tokens = set(re.findall(r"[a-z][a-z'-]{2,}", original.casefold()))
    canonical_tokens = set(re.findall(r"[a-z][a-z'-]{2,}", canonical.casefold()))
    copied_terms = (source_tokens & canonical_tokens) - _GENERIC_TERMS
    if proper_nouns:
        return proper_nouns
    return copied_terms if len(copied_terms) >= 2 else set()


def cluster_audit_schema():
    return {"type": "object", "properties": {
        "cluster_id": {"type": "integer"}, "main_reasoning_relation": _string(),
        "shared_invariant": _string(), "variation_within_cluster": _string(),
        "member_consistency": {"enum": ["HIGH", "MEDIUM", "LOW"]},
        "medoid_representative": {"enum": ["YES", "PARTIAL", "NO"]},
        "secondary_patterns": {"type": "array", "items": _string(), "maxItems": 20},
        "outlier_ids": {"type": "array", "items": _string(200), "maxItems": 100},
        "possible_semantic_extraction_errors": {"type": "array", "items": _string(), "maxItems": 20},
        "possible_mislabel_or_intrinsic_overlap": {"type": "array", "items": _string(), "maxItems": 20},
    }, "required": ["cluster_id", "main_reasoning_relation", "shared_invariant", "variation_within_cluster",
                       "member_consistency", "medoid_representative", "secondary_patterns", "outlier_ids",
                       "possible_semantic_extraction_errors", "possible_mislabel_or_intrinsic_overlap"],
    "additionalProperties": False}


def cluster_mode_schema():
    return {"type": "object", "properties": {
        "cluster_id": {"type": "integer"}, "mode_name": _string(), "premise_pattern": _string(),
        "conclusion_pattern": _string(), "core_bridge": _string(), "canonical_template": _string(),
        "non_invariant_details": {"type": "array", "items": _string(), "maxItems": 30},
        "boundary_notes": {"type": "array", "items": _string(), "maxItems": 30},
        "supporting_member_ids": {"type": "array", "items": _string(200), "minItems": 1, "maxItems": 1000},
        "coverage_n": {"type": "integer"},
    }, "required": ["cluster_id", "mode_name", "premise_pattern", "conclusion_pattern", "core_bridge",
                       "canonical_template", "non_invariant_details", "boundary_notes", "supporting_member_ids", "coverage_n"],
    "additionalProperties": False}


def validate_cluster_audit(value):
    validate_output(value, cluster_audit_schema())
    return value


def validate_cluster_mode(value):
    validate_output(value, cluster_mode_schema())
    return value


def validate_merge_plan(value):
    validate_output(value, merge_plan_schema())
    return value


def final_definition_schema():
    mode = {"type": "object", "properties": {
        "cluster_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
        "mode_name": _string(), "coverage_n": {"type": "integer"}, "relation": _string(),
        "supporting_member_ids": {"type": "array", "items": _string(200), "minItems": 1},
    }, "required": ["cluster_ids", "mode_name", "coverage_n", "relation", "supporting_member_ids"], "additionalProperties": False}
    return {"type": "object", "properties": {
        "status": {"enum": ["INDUCTION READY", "PARTIALLY READY", "NOT READY"]},
        "core_invariant": _string(), "prototypical_relation": _string(),
        "discovered_modes": {"type": "array", "items": mode, "maxItems": 100},
        "not_sufficient": {"type": "array", "items": _string(), "maxItems": 50},
        "opposite_direction_cases": {"type": "array", "items": _string(), "maxItems": 50},
        "descriptive_cases": {"type": "array", "items": _string(), "maxItems": 50},
        "dataset_edge_modes": {"type": "array", "items": _string(), "maxItems": 50},
        "operational_classification_test": {"type": "array", "items": _string(), "minItems": 1, "maxItems": 20},
    }, "required": ["status", "core_invariant", "prototypical_relation", "discovered_modes", "not_sufficient",
                       "opposite_direction_cases", "descriptive_cases", "dataset_edge_modes", "operational_classification_test"],
    "additionalProperties": False}


def validate_final_definition(value):
    validate_output(value, final_definition_schema())
    return value


def merge_plan_schema():
    item = {"type": "object", "properties": {"cluster_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 2},
        "reason": _string(), "merged_mode": _string()}, "required": ["cluster_ids", "reason", "merged_mode"], "additionalProperties": False}
    separate = {"type": "object", "properties": {"cluster_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 2},
        "reason": _string()}, "required": ["cluster_ids", "reason"], "additionalProperties": False}
    return {"type": "object", "properties": {"merge_groups": {"type": "array", "items": item, "maxItems": 100},
        "keep_separate": {"type": "array", "items": separate, "maxItems": 100}}, "required": ["merge_groups", "keep_separate"], "additionalProperties": False}

