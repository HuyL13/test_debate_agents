import pytest

from src.schemas import arbiter_schema, validate_output, validate_arbiter_semantics


@pytest.mark.parametrize("candidate", [None, "Slippery Slope"])
def test_arbiter_has_one_decision_with_explanation(candidate):
    output = {"selected_candidate": candidate, "evidence_spans": ["It gets worse"],
              "decisive_condition": "The alleged escalation must be supported.",
              "decision_reason": "The target's causal links determine whether the hypothesis holds."}
    schema = arbiter_schema("detection", ["Slippery Slope"])
    validate_output(output, schema)
    validate_arbiter_semantics(output, ["Slippery Slope"])
    assert "verified" not in schema["properties"]
    assert "rejection_reason" not in schema["properties"]


def test_arbiter_still_rejects_non_surviving_candidate():
    with pytest.raises(ValueError, match="non-surviving"):
        validate_arbiter_semantics({"selected_candidate": "False Dilemma"}, ["Slippery Slope"])
