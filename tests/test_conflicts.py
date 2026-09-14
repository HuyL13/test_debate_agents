from src.conflicts import build_conflicts


def test_detects_candidate_disagreement_pair():
    reports = {
        "scheme": {"candidate": "Slippery Slope", "evidence_spans": ["A leads to B"]},
        "enthymeme": {"candidate": "Hasty Generalization", "evidence_spans": ["these cases prove it"]},
        "critical": {"candidate": "Slippery Slope", "evidence_spans": ["B then C"]},
    }

    conflicts = build_conflicts(reports)

    assert conflicts[0]["id"] == "hasty-generalization__vs__slippery-slope"
    assert conflicts[0]["candidates"] == ["Hasty Generalization", "Slippery Slope"]


def test_detects_candidate_vs_none_and_structural_conflict():
    reports = {
        "scheme": {
            "candidate": "False Dilemma",
            "evidence_spans": ["good and evil"],
            "structure_complete": False,
        },
        "enthymeme": {
            "candidate": "False Dilemma",
            "evidence_spans": ["good and evil"],
            "required_assumption": "the options are exhaustive",
            "assumption_licensed": False,
        },
        "critical": {
            "candidate": None,
            "evidence_spans": ["good and evil"],
            "criterion": "exhaustiveness commitment",
            "criterion_met": False,
        },
    }

    conflicts = build_conflicts(reports)

    assert conflicts[0]["id"] == "false-dilemma__vs__non-fallacious"
    assert conflicts[0]["type"] == "structural_conflict"
    assert "scheme.structure_complete=false" in conflicts[0]["triggered_by"]
    assert "enthymeme.assumption_licensed=false" in conflicts[0]["triggered_by"]
    assert "critical.criterion_met=false" in conflicts[0]["triggered_by"]
