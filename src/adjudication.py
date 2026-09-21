from src.labels import ANALYSTS, FALLACIES, labels_for


def _report_view(role, report):
    return {
        "source": role,
        "verdict": report["verdict"],
        "candidate": report["candidate"],
        "mandatory_condition": report["mandatory_condition"],
        "condition_satisfied": report["condition_satisfied"],
        "decision_reason": report["decision_reason"],
        "opposing_reason": report["opposing_reason"],
        "evidence_ids": report.get("evidence_ids", []),
        "evidence_spans": report.get("evidence_spans", []),
    }


def build_candidate_dossiers(task, reports):
    labels_for(task)
    candidates = []
    for role in ANALYSTS:
        candidate = reports[role].get("candidate")
        if candidate is not None and candidate not in candidates:
            candidates.append(candidate)

    dossiers = []
    for candidate in candidates:
        support = []
        opposition = []
        for role in ANALYSTS:
            report = reports[role]
            view = _report_view(role, report)
            if report.get("candidate") == candidate and report["verdict"] == "Fallacious":
                support.append(view)
            else:
                opposition.append(view)
        dossiers.append({
            "candidate": candidate,
            "status": "contested" if opposition else "supported",
            "support": support,
            "opposition": opposition,
        })
    return dossiers


def adjudication_route(task, dossiers):
    labels_for(task)
    candidates = [item["candidate"] for item in dossiers]
    if task == "detection":
        return {
            "action": "adjudicate",
            "recovery": not candidates,
            "allowed_candidates": candidates or list(FALLACIES),
        }
    if not candidates:
        return {
            "action": "adjudicate",
            "recovery": True,
            "allowed_candidates": list(FALLACIES),
        }
    if len(dossiers) == 1 and dossiers[0]["status"] == "supported":
        return {
            "action": "direct",
            "recovery": False,
            "allowed_candidates": candidates,
            "selected_candidate": candidates[0],
        }
    return {
        "action": "adjudicate",
        "recovery": False,
        "allowed_candidates": candidates,
    }
