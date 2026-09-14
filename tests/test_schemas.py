import pytest

from src.schemas import scheme_schema, validate_evidence_spans, validate_output


def test_schema_rejects_confidence_and_content_blob():
    schema = scheme_schema("detection")
    output = {
        "candidate": "False Dilemma",
        "evidence_spans": ["good and evil"],
        "relation": "moral contrast",
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
