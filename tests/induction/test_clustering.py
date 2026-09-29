import numpy as np

from src.induction.clustering import (
    choose_medoid,
    cosine_distance_matrix,
    fit_kmedoids,
    search_k,
    select_member_audit_rows,
)
from src.induction.config import load_config_from_mapping


def test_choose_medoid_returns_an_actual_member():
    distances = np.array([[0.0, 0.2, 0.8], [0.2, 0.0, 0.3], [0.8, 0.3, 0.0]])
    assert choose_medoid([0, 1, 2], distances) == 1


def test_kmedoids_is_reproducible_for_same_seed():
    embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])
    distance = cosine_distance_matrix(embeddings)
    first = fit_kmedoids(distance, k=2, seed=42, restarts=3)
    second = fit_kmedoids(distance, k=2, seed=42, restarts=3)
    assert first["labels"].tolist() == second["labels"].tolist()
    assert first["medoid_indices"].tolist() == second["medoid_indices"].tolist()


def test_member_audit_has_medoid_nearest_and_boundary_members():
    embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])
    distance = cosine_distance_matrix(embeddings)
    fitted = fit_kmedoids(distance, k=2, seed=42, restarts=3)
    records = [{"sample_id": f"1:c{i}", "canonical_reasoning": "reason"} for i in range(4)]
    rows = select_member_audit_rows(fitted, records, distance, nearest_n=1, farthest_n=1)
    assert {row["kind"] for row in rows} == {"medoid", "nearest", "boundary"}


def test_search_k_does_not_require_removed_semantic_fields(tmp_path):
    config = load_config_from_mapping({
        "base_dir": str(tmp_path),
        "data": {"path": "train.json", "label": "appeal to tradition"},
        "output_dir": "output",
        "clustering": {"k_min": 2, "k_max": 2},
    })
    embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]])
    records = [{"sample_id": f"1:c{i}", "original_text": "text", "canonical_reasoning": "reason"} for i in range(4)]

    result = search_k(config, embeddings, records)

    assert "relation_polarity_purity" not in result["metrics"][0]
    assert "conclusion_direction_purity" not in result["metrics"][0]
    assert "premise_valence_purity" not in result["metrics"][0]
