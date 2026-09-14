import pytest

from src.schemas import critical_schema, scheme_schema, validate_evidence_spans, validate_output


def test_schema_rejects_confidence_and_content_blob():
    schema = scheme_schema("detection")
    output = {
        "candidate": "False Dilemma",
        "evidence_spans": ["good and evil"],
        "relation": "alternatives_to_choice",
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


def test_scheme_relation_is_known_structural_relation():
    with pytest.raises(ValueError):
        validate_output(
            {
                "candidate": "False Dilemma",
                "evidence_spans": ["good and evil"],
                "relation": "cocolo-fa",
                "structure_complete": False,
            },
            scheme_schema("detection"),
        )


def test_critical_criterion_is_known_and_alternative_reading_can_be_null():
    validate_output(
        {
            "candidate": "Slippery Slope",
            "evidence_spans": ["It only gets worse"],
            "criterion": "consequence_progression",
            "criterion_met": True,
            "alternative_reading": None,
        },
        critical_schema("detection"),
    )
    with pytest.raises(ValueError):
        validate_output(
            {
                "candidate": "Slippery Slope",
                "evidence_spans": ["It only gets worse"],
                "criterion": "True",
                "criterion_met": True,
                "alternative_reading": "No",
            },
            critical_schema("detection"),
        )
