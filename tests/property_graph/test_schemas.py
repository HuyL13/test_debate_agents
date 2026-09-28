from copy import deepcopy

import pytest

from src.property_graph.schemas import validate_graph, validate_signature


@pytest.fixture
def valid_signature():
    return {
        "sample_id": "1:2",
        "propositions": [
            {"id": "p1", "text": "Experts agree", "speaker": "target", "role": "premise"},
            {"id": "p2", "text": "It is true", "speaker": "target", "role": "conclusion"},
        ],
        "relations": [{
            "source": "p1",
            "target": "p2",
            "type": "USED_AS_JUSTIFICATION",
            "status": "asserted",
            "explicitness": "explicit",
            "evidence_spans": ["Experts agree"],
        }],
        "semantic_roles": {
            "source_type": "expert",
            "sample_scope": "individual",
            "target_scope": "universal",
            "alternatives_count": None,
            "property_type": "expertise",
            "comparison_target": None,
        },
        "qualifiers": {"certainty": "high", "universality": "universal", "normative": False},
        "structural_features": ["premise_to_conclusion"],
        "uncertainties": [],
    }


def test_signature_accepts_valid_structure(valid_signature):
    assert validate_signature(valid_signature, "Experts agree. It is true.") == valid_signature


def test_signature_rejects_missing_relation_endpoint(valid_signature):
    signature = deepcopy(valid_signature)
    signature["relations"][0]["target"] = "missing"
    with pytest.raises(ValueError, match="relation endpoint"):
        validate_signature(signature, "Experts agree. It is true.")


def test_signature_rejects_unseen_evidence(valid_signature):
    signature = deepcopy(valid_signature)
    signature["relations"][0]["evidence_spans"] = ["gold says so"]
    with pytest.raises(ValueError, match="evidence span"):
        validate_signature(signature, "Experts agree. It is true.")


def test_signature_rejects_runaway_relation_output(valid_signature):
    signature = deepcopy(valid_signature)
    signature["relations"] = signature["relations"] * 7
    with pytest.raises(ValueError, match="item count"):
        validate_signature(signature, "Experts agree. It is true.")


def test_graph_rejects_dangling_edge():
    graph = {
        "meta": {},
        "nodes": [],
        "edges": [{
            "id": "e1",
            "source": "missing",
            "target": "also-missing",
            "type": "HAS_PROTOTYPE",
            "weight": 1.0,
            "support_count": 0,
            "attrs": {},
            "provenance": [],
        }],
    }
    with pytest.raises(ValueError, match="endpoint"):
        validate_graph(graph)
