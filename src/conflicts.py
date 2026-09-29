KNOWN_PAIR_PRIORITY = [
    ("Hasty Generalization", "Slippery Slope"),
    ("Appeal to Majority", "Appeal to Authority"),
    ("Appeal to Tradition", "Appeal to Worse Problems"),
]

DISCRIMINATORS = {
    frozenset(("Hasty Generalization", "Slippery Slope")): (
        "Hasty Generalization requires explicit cases/sample -> broader population/class. "
        "Slippery Slope requires action/condition -> progressively worse consequences."
    ),
    frozenset(("Appeal to Majority", "Appeal to Authority")): (
        "Majority uses number/popularity as justification; Authority uses expertise/status."
    ),
    frozenset(("Appeal to Tradition", "Appeal to Worse Problems")): (
        "Tradition uses longevity to justify preservation. Worse Problems uses a larger/worse "
        "issue to downplay or deprioritize another issue."
    ),
}


def slug(label):
    return "non-fallacious" if label is None else label.lower().replace(" ", "-")


def pair_id(a, b):
    ordered = sorted((a, b), key=slug)
    return f"{slug(ordered[0])}__vs__{slug(ordered[1])}"


def _unique(values):
    out = []
    for value in values:
        if value is not None and value not in out:
            out.append(value)
    return out


def choose_next_conflict(candidates):
    candidates = _unique(candidates)
    if len(candidates) <= 1:
        return None

    pair = None
    candidate_set = set(candidates)

    for known in KNOWN_PAIR_PRIORITY:
        if set(known).issubset(candidate_set):
            pair = list(known)
            break

    if pair is None:
        pair = sorted(candidates, key=slug)[:2]

    return {
        "id": pair_id(pair[0], pair[1]),
        "type": "candidate_disagreement",
        "candidates": pair,
        "triggered_by": ["surviving_candidate_disagreement"],
        "discriminator": DISCRIMINATORS.get(
            frozenset(pair),
            "Compare only these candidates. Select the one whose mandatory structural "
            "condition is directly supported by TARGET."
        ),
    }
