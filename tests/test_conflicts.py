from src.conflicts import choose_next_conflict


def test_detects_known_candidate_disagreement_pair():
    conflict = choose_next_conflict(["Slippery Slope", "Hasty Generalization"])

    assert conflict["id"] == "hasty-generalization__vs__slippery-slope"
    assert conflict["candidates"] == ["Hasty Generalization", "Slippery Slope"]
    assert conflict["type"] == "candidate_disagreement"


def test_dynamic_conflict_returns_none_for_zero_or_one_survivor():
    assert choose_next_conflict([]) is None
    assert choose_next_conflict(["Slippery Slope"]) is None


def test_unknown_pair_is_bounded_to_two_surviving_candidates():
    conflict = choose_next_conflict([
        "False Dilemma",
        "Appeal to Authority",
        "Slippery Slope",
    ])

    assert len(conflict["candidates"]) == 2
    assert set(conflict["candidates"]).issubset({
        "False Dilemma",
        "Appeal to Authority",
        "Slippery Slope",
    })
