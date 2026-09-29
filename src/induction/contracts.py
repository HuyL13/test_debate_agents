from src.schemas import validate_output


def _string(max_length=2000):
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def _nullable_string(max_length=2000):
    return {"anyOf": [_string(max_length), {"type": "null"}]}


def semantic_schema():
    return {
        "type": "object",
        "properties": {
            "article_id": {"type": "integer"},
            "comment_id": _string(200),
            "original_text": _string(10000),
            "premises": {"type": "array", "items": _string(2000), "minItems": 1, "maxItems": 8},
            "conclusion": _string(),
            "inference_source": _string(),
            "inference_target": _string(),
            "bridge": _string(),
            "evidential_basis": _string(),
            "premise_valence": {"enum": ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED", "UNKNOWN"]},
            "relation_polarity": {"enum": ["SUPPORTS_CONTINUITY", "SUPPORTS_CHANGE", "SUPPORTS_ACCEPTANCE", "SUPPORTS_REJECTION", "PREDICTIVE_DESCRIPTIVE", "OTHER"]},
            "conclusion_direction": _string(300),
            "missing_justification": _nullable_string(),
            "alternatives_suppressed": _nullable_string(),
            "causal_chain": _nullable_string(),
            "canonical_reasoning": _string(2000),
            "ambiguity_notes": _nullable_string(),
            "topic_leakage_check": {"type": "boolean"},
        },
        "required": [
            "article_id", "comment_id", "original_text", "premises", "conclusion",
            "inference_source", "inference_target", "bridge", "evidential_basis",
            "premise_valence", "relation_polarity", "conclusion_direction",
            "missing_justification", "alternatives_suppressed", "causal_chain",
            "canonical_reasoning", "ambiguity_notes", "topic_leakage_check",
        ],
        "additionalProperties": False,
    }


def validate_semantic_record(record, sample):
    validate_output(record, semantic_schema())
    if record["article_id"] != sample["article_id"] or record["comment_id"] != sample["comment_id"]:
        raise ValueError("semantic record ID does not match sample")
    if record["original_text"] != sample["comment"]:
        raise ValueError("original_text must preserve the target comment")
    if not record["canonical_reasoning"].strip():
        raise ValueError("canonical_reasoning must be non-empty")
    if len(record["canonical_reasoning"].split()) < 4:
        raise ValueError("canonical_reasoning is too short to preserve inference")
    return record


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


def merge_plan_schema():
    item = {"type": "object", "properties": {"cluster_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 2},
        "reason": _string(), "merged_mode": _string()}, "required": ["cluster_ids", "reason", "merged_mode"], "additionalProperties": False}
    separate = {"type": "object", "properties": {"cluster_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 2},
        "reason": _string()}, "required": ["cluster_ids", "reason"], "additionalProperties": False}
    return {"type": "object", "properties": {"merge_groups": {"type": "array", "items": item, "maxItems": 100},
        "keep_separate": {"type": "array", "items": separate, "maxItems": 100}}, "required": ["merge_groups", "keep_separate"], "additionalProperties": False}

