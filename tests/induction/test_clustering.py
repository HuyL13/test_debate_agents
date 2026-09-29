import numpy as np

from src.induction.clustering import (
    choose_medoid,
    cosine_distance_matrix,
    fit_kmedoids,
    select_member_audit_rows,
)


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
