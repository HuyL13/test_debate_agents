import pytest
from src.schemas import derive_candidate, STRUCTURE_BY_CANDIDATE


@pytest.mark.parametrize("role,field,mapping", [
    ("structure", "structure_type", STRUCTURE_BY_CANDIDATE),
])
def test_candidates_are_derived_from_expert_analysis(role, field, mapping):
    assert len(mapping) == len(set(mapping.values())) == 8
    for label, kind in mapping.items():
        assert derive_candidate(role, {field: kind}) == label
    assert derive_candidate(role, {field: "none"}) is None
    if role != "structure":
        assert derive_candidate(role, {field: "other"}) is None


def test_experts_do_not_request_redundant_candidate():
    for factory in (structure_schema,):
        schema = factory("detection")
        assert "candidate" not in schema["properties"]
        assert schema["additionalProperties"] is False


from src.schemas import (
    counterargument_schema,
    goal_schema,
    structure_schema,
    validate_counterargument_semantics,
    validate_evidence_spans,
    validate_goal_semantics,
    validate_output,
    validate_structure_semantics,
)


def test_schema_rejects_confidence_and_content_blob():
    schema = structure_schema("detection")
    output = {
        "evidence_spans": ["good and evil"],
        "structure_type": "exhaustive_alternatives",
        "slots": [],
        "structure_complete": False,
        "confidence": 0.5,
    }

    with pytest.raises(ValueError):
        validate_output(output, schema)


def test_evidence_spans_must_be_short_substrings_of_target():
    validate_evidence_spans(
        {"evidence_spans": ["good and evil"]},
        "This election is about good and evil.",
    )

    with pytest.raises(ValueError, match="not found"):
        validate_evidence_spans({"evidence_spans": ["missing span"]}, "target text")


@pytest.mark.parametrize("span", ["I think we  need to look.  ", "I think we need to look."])
def test_evidence_whitespace_is_restored_to_exact_target(span):
    target = "I think we  need to look. Another sentence."
    report = {"evidence_spans": [span]}
    validate_evidence_spans(report, target)
    assert report["evidence_spans"] == ["I think we  need to look."]
    assert report["evidence_spans"][0] in target


@pytest.mark.parametrize("span", ["we must look", "we need look", "   ", "parent only"])
def test_evidence_normalization_does_not_accept_changed_words(span):
    with pytest.raises(ValueError, match="not found"):
        validate_evidence_spans({"evidence_spans": [span]}, "we  need to look")


def test_structure_candidate_type_mapping_and_slots_are_enforced():
    valid = {
        "evidence_spans": ["It only gets worse"],
        "structure_type": "consequence_chain",
        "slots": [
            {"role": "initial_event", "text": "Once you let them dictate rules against fairness"},
            {"role": "intermediate_consequence", "text": "It only gets worse"},
            {"role": "final_consequence", "text": "Rights will be trampled and compromised"},
        ],
        "structure_complete": True,
    }
    validate_output(valid, structure_schema("detection"))
    validate_structure_semantics(valid)

    with pytest.raises(ValueError, match="missing required slots"):
        validate_structure_semantics({**valid, "structure_type": "sample_to_population"})

    with pytest.raises(ValueError, match="missing required slots"):
        validate_structure_semantics({**valid, "slots": [], "structure_complete": True})


def test_appeal_to_majority_requires_target_claim_slot():
    valid = {
        "evidence_spans": ["Most people support it"],
        "structure_type": "popularity_to_claim",
        "slots": [
            {"role": "population_group", "text": "Most people"},
            {"role": "popularity_claim", "text": "support it"},
            {"role": "target_claim", "text": "it"},
        ],
        "structure_complete": True,
    }
    validate_output(valid, structure_schema("detection"))
    validate_structure_semantics(valid)

    with pytest.raises(ValueError, match="missing required slots"):
        validate_structure_semantics({**valid, "slots": valid["slots"][:2]})


def test_goal_and_counterargument_preserve_independent_candidates():
    for role in ("goal", "counterargument"):
        assert derive_candidate(role, {"candidate": "Appeal to Nature"}) == "Appeal to Nature"
        assert derive_candidate(role, {"candidate": None}) is None


def test_legacy_categorical_fields_are_not_requested():
    assert "support_mechanism" not in goal_schema("detection")["properties"]
    assert "failure_mode" not in counterargument_schema("detection")["properties"]
