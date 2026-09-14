KNOWN_PAIR_PRIORITY = [
    ("Hasty Generalization", "Slippery Slope"),
    ("False Dilemma", None),
    ("Appeal to Majority", "Appeal to Authority"),
    ("Appeal to Tradition", "Appeal to Worse Problems"),
]

DISCRIMINATORS = {
    ("Hasty Generalization", "Slippery Slope"): (
        "HG requires cases -> broader population. SS requires event -> consequence -> escalation."
    ),
    ("False Dilemma", None): (
        "Does TARGET commit to alternatives being exhaustive? Mere contrast or good-vs-evil rhetoric is insufficient."
    ),
    ("Appeal to Majority", "Appeal to Authority"): (
        "Number/popularity supports Majority; expertise/status supports Authority."
    ),
    ("Appeal to Tradition", "Appeal to Worse Problems"): (
        "Longevity -> preserve is Tradition. Worse/larger issue -> deprioritize another is Worse Problems."
    ),
}


def slug(label):
    return "non-fallacious" if label is None else label.lower().replace(" ", "-")


def pair_id(a, b):
    ordered = sorted([a, b], key=slug)
    return f"{slug(ordered[0])}__vs__{slug(ordered[1])}"


def _ordered_pair(candidates):
    for known in KNOWN_PAIR_PRIORITY:
        if set(known) <= set(candidates):
            return list(known)
    return sorted(candidates, key=slug)[:2]


def _conflict(pair, ctype, triggers):
    return {
        "id": pair_id(pair[0], pair[1]),
        "type": ctype,
        "candidates": pair,
        "triggered_by": triggers or ["candidate_disagreement"],
        "discriminator": DISCRIMINATORS.get(tuple(pair)) or DISCRIMINATORS.get(tuple(reversed(pair))) or (
            "Compare only these candidates and choose the one whose mandatory structure is directly supported by TARGET."
        ),
    }


def _structural_triggers(reports):
    triggers = []
    scheme = reports.get("scheme", {})
    enthymeme = reports.get("enthymeme", {})
    critical = reports.get("critical", {})
    if scheme.get("candidate") and scheme.get("structure_complete") is False:
        triggers.append("scheme.structure_complete=false")
    if enthymeme.get("candidate") and enthymeme.get("assumption_licensed") is False:
        triggers.append("enthymeme.assumption_licensed=false")
    if critical.get("candidate") is not None and critical.get("criterion_met") is False:
        triggers.append("critical.criterion_met=false")
    if critical.get("candidate") is None and any(r.get("candidate") for r in reports.values()):
        triggers.append("critical.criterion_met=false")
    return triggers


def build_conflicts(reports):
    candidates = {reports[role].get("candidate") for role in ("scheme", "enthymeme", "critical")}
    triggers = _structural_triggers(reports)
    non_null = {candidate for candidate in candidates if candidate is not None}
    if len(candidates) <= 1 and not triggers:
        return []
    ctype = "structural_conflict" if triggers else "candidate_disagreement"
    if len(non_null) == 1 and triggers:
        pair = [next(iter(non_null)), None]
        return [_conflict(pair, ctype, triggers)]
    if None in candidates and len(non_null) == 1:
        pair = [next(iter(non_null)), None]
    else:
        pair = _ordered_pair(candidates)
    conflicts = [_conflict(pair, ctype, triggers)]
    remaining = sorted((candidate for candidate in candidates if candidate not in pair), key=slug)
    if remaining:
        conflicts.append(_conflict([pair[1], remaining[0]], "candidate_disagreement", ["candidate_disagreement"]))
    return conflicts[:2]
