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


def test_structure_requests_candidate_for_cross_role_dossiers():
    schema = structure_schema("detection")
    assert "candidate" in schema["properties"]
    assert schema["additionalProperties"] is False


from src.schemas import (
    comparative_adjudicator_schema,
    counterargument_schema,
    goal_schema,
    structure_schema,
    validate_counterargument_semantics,
    validate_comparative_adjudicator_semantics,
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
        "verdict": "Fallacious",
        "candidate": "Slippery Slope",
        "mandatory_condition": "An unsupported escalation links an action to severe consequences.",
        "condition_satisfied": True,
        "opposing_reason": "The passage could be read as a supported warning.",
        "structure_type": "consequence_chain",
        "slots": [
            {"role": "initial_event", "text": "Once you let them dictate rules against fairness"},
            {"role": "intermediate_consequence", "text": "It only gets worse"},
            {"role": "final_consequence", "text": "Rights will be trampled and compromised"},
        ],
        "structure_complete": True,
        "premise": "They are allowed to dictate rules.",
        "conclusion": "Rights will be trampled.",
        "inferential_link": "The initial action is claimed to escalate.",
    }
    validate_output(valid, structure_schema("detection"))
    validate_structure_semantics(valid)

    with pytest.raises(ValueError, match="missing required slots"):
        validate_structure_semantics({
            **valid,
            "candidate": "Hasty Generalization",
            "structure_type": "sample_to_population",
        })

    with pytest.raises(ValueError, match="missing required slots"):
        validate_structure_semantics({**valid, "slots": [], "structure_complete": True})


def test_appeal_to_majority_requires_target_claim_slot():
    valid = {
        "evidence_spans": ["Most people support it"],
        "verdict": "Fallacious",
        "candidate": "Appeal to Majority",
        "mandatory_condition": "Popularity is used as proof of the target claim.",
        "condition_satisfied": True,
        "opposing_reason": "Popularity may only provide context.",
        "structure_type": "popularity_to_claim",
        "slots": [
            {"role": "population_group", "text": "Most people"},
            {"role": "popularity_claim", "text": "support it"},
            {"role": "target_claim", "text": "it"},
        ],
        "structure_complete": True,
        "premise": "Most people support it.",
        "conclusion": "It is correct.",
        "inferential_link": "Popularity is treated as proof.",
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


def test_analyst_contracts_require_balanced_verdict_fields():
    common = {
        "verdict",
        "candidate",
        "mandatory_condition",
        "condition_satisfied",
        "opposing_reason",
    }
    for factory in (structure_schema, goal_schema, counterargument_schema):
        assert common <= set(factory("detection")["required"])

    counter_fields = set(counterargument_schema("detection")["required"])
    assert {"strongest_objection", "strongest_defense", "winning_side"} <= counter_fields


def test_detection_report_rejects_candidate_verdict_mismatch():
    value = {
        "evidence_spans": ["target"],
        "conclusion_or_goal": "A conclusion.",
        "candidate": "False Dilemma",
        "supporting_reason": "A reason.",
        "support_relation": "A relation.",
        "label_justification": "A justification.",
        "mechanism_supports_goal": True,
        "verdict": "Non-Fallacious",
        "mandatory_condition": "Alternatives are exhaustive.",
        "condition_satisfied": True,
        "opposing_reason": "The alternatives may not be exhaustive.",
        "fallacy_owned_by_target": True,
    }

    validate_output(value, goal_schema("detection"))
    with pytest.raises(ValueError, match="negative verdict"):
        validate_goal_semantics(value, "detection")


def test_comparative_adjudicator_enforces_detection_verdict_and_candidate():
    schema = comparative_adjudicator_schema("detection", ["False Dilemma"])
    value = {
        "selected_verdict": "Non-Fallacious",
        "selected_candidate": "False Dilemma",
        "evidence_spans": ["target"],
        "decisive_condition": "No exhaustive alternatives are asserted.",
        "decision_reason": "The proposed structure is absent.",
        "rejected_candidates": [
            {"candidate": "False Dilemma", "failed_condition": "No exhaustive commitment."}
        ],
    }

    validate_output(value, schema)
    with pytest.raises(ValueError, match="negative verdict"):
        validate_comparative_adjudicator_semantics(
            value,
            "detection",
            ["False Dilemma"],
        )
