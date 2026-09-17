import pytest

from src.schemas import goal_schema, counterargument_schema, validate_output, validate_goal_semantics


def test_goal_can_describe_a_warning_without_calling_it_fallacious():
    report = {
        "candidate": None,
        "evidence_spans": ["It may get worse"],
        "conclusion_or_goal": "Exercise caution",
        "supporting_reason": "Potential adverse consequences",
        "support_relation": "The risk motivates caution without asserting inevitability.",
        "label_justification": "A warning alone does not establish a slippery slope.",
        "mechanism_supports_goal": True,
    }
    validate_output(report, goal_schema("detection"))
    validate_goal_semantics(report)


def test_counterargument_proposes_label_with_specific_objection():
    report = {
        "candidate": "Slippery Slope",
        "evidence_spans": ["It only gets worse"],
        "challenged_inference": "An initial action necessarily escalates into rights loss.",
        "decisive_counterargument": "The links between successive consequences are not established.",
        "label_justification": "This concerns escalation, not generalizing observed cases.",
        "failure_exposed": True,
    }
    validate_output(report, counterargument_schema("detection"))


def test_nonnull_goal_requires_rationale():
    report = {"candidate": "Slippery Slope", "conclusion_or_goal": "Oppose rules",
              "supporting_reason": "Rights loss", "support_relation": "A warning",
              "label_justification": "   ", "mechanism_supports_goal": True}
    with pytest.raises(ValueError, match="label_justification"):
        validate_goal_semantics(report)
