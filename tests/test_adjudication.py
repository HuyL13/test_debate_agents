from src.adjudication import adjudication_route, build_candidate_dossiers


def report(verdict, candidate, condition, satisfied, opposing):
    return {
        "verdict": verdict,
        "candidate": candidate,
        "mandatory_condition": condition,
        "condition_satisfied": satisfied,
        "decision_reason": (
            "The mandatory condition is satisfied."
            if verdict == "Fallacious"
            else "No listed fallacy's mandatory condition is satisfied."
        ),
        "opposing_reason": opposing,
        "evidence_ids": ["T1"],
    }


def test_contested_candidate_survives_with_source_condition_attached():
    reports = {
        "structure": report(
            "Fallacious",
            "Slippery Slope",
            "An unsupported consequence progression is asserted.",
            True,
            "The progression may be a proportionate warning.",
        ),
        "goal": report(
            "Non-Fallacious",
            None,
            None,
            False,
            "The warning may still overstate an escalation.",
        ),
        "counterargument": report(
            "Fallacious",
            "Hasty Generalization",
            "A sample is generalized to a broader population.",
            True,
            "No population generalization may be intended.",
        ),
    }

    dossiers = build_candidate_dossiers("detection", reports)

    assert [item["candidate"] for item in dossiers] == [
        "Slippery Slope",
        "Hasty Generalization",
    ]
    slippery = dossiers[0]
    assert slippery["status"] == "contested"
    assert slippery["support"][0]["mandatory_condition"] == (
        "An unsupported consequence progression is asserted."
    )
    assert slippery["support"][0]["source"] == "structure"
    assert slippery["opposition"][0]["source"] == "goal"


def test_detection_always_routes_to_comparative_adjudication():
    reports = {
        role: report("Non-Fallacious", None, None, False, "A possible positive reading.")
        for role in ("structure", "goal", "counterargument")
    }

    route = adjudication_route("detection", build_candidate_dossiers("detection", reports))

    assert route["action"] == "adjudicate"
    assert route["recovery"] is True
    assert len(route["allowed_candidates"]) == 8


def test_classification_shortcuts_only_uncontested_unanimous_candidate():
    reports = {
        role: report(
            "Fallacious",
            "False Dilemma",
            "Alternatives are presented as exhaustive.",
            True,
            "The alternatives may not be exhaustive.",
        )
        for role in ("structure", "goal", "counterargument")
    }
    dossiers = build_candidate_dossiers("classification", reports)

    assert adjudication_route("classification", dossiers) == {
        "action": "direct",
        "recovery": False,
        "allowed_candidates": ["False Dilemma"],
        "selected_candidate": "False Dilemma",
    }


def test_classification_contested_singleton_still_routes_to_adjudicator():
    reports = {
        "structure": report(
            "Fallacious", "False Dilemma", "Alternatives are exhaustive.", True,
            "The alternatives may not be exhaustive.",
        ),
        "goal": report("Non-Fallacious", None, None, False, "A dilemma may be implicit."),
        "counterargument": report(
            "Fallacious", "False Dilemma", "Alternatives are exhaustive.", True,
            "The alternatives may not be exhaustive.",
        ),
    }

    route = adjudication_route(
        "classification",
        build_candidate_dossiers("classification", reports),
    )

    assert route["action"] == "adjudicate"
    assert route["allowed_candidates"] == ["False Dilemma"]
