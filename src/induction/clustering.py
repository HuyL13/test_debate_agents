import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_distances

from src.io_utils import write_json


def cosine_distance_matrix(embeddings):
    values = np.asarray(embeddings, dtype=float)
    if values.ndim != 2 or len(values) < 2:
        raise ValueError("at least two embedding vectors are required")
    return cosine_distances(values)


def choose_medoid(indices, distance_matrix):
    indices = np.asarray(list(indices), dtype=int)
    if len(indices) == 0:
        raise ValueError("cannot choose a medoid from an empty cluster")
    local = distance_matrix[np.ix_(indices, indices)]
    scores = local.mean(axis=1)
    return int(indices[int(np.argmin(scores))])


def _assign(distance_matrix, medoids):
    medoids = np.asarray(medoids, dtype=int)
    distances = distance_matrix[:, medoids]
    return np.argmin(distances, axis=1)


def _single_kmedoids(distance_matrix, medoids):
    medoids = np.asarray(sorted(set(int(value) for value in medoids)), dtype=int)
    for _ in range(100):
        labels = _assign(distance_matrix, medoids)
        updated = []
        for cluster_id in range(len(medoids)):
            members = np.flatnonzero(labels == cluster_id)
            if len(members) == 0:
                candidates = [index for index in range(len(distance_matrix)) if index not in updated]
                updated.append(candidates[0])
            else:
                updated.append(choose_medoid(members, distance_matrix))
        updated = np.asarray(sorted(updated), dtype=int)
        if np.array_equal(updated, medoids):
            labels = _assign(distance_matrix, updated)
            break
        medoids = updated
    labels = _assign(distance_matrix, medoids)
    objective = float(sum(distance_matrix[index, medoids[labels[index]]] for index in range(len(labels))))
    return {"labels": labels, "medoid_indices": medoids, "objective": objective}


def fit_kmedoids(distance_matrix, k, seed=42, restarts=10):
    distance_matrix = np.asarray(distance_matrix, dtype=float)
    n = len(distance_matrix)
    if distance_matrix.shape != (n, n) or not 2 <= k <= n:
        raise ValueError("distance matrix and k are invalid")
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(max(1, int(restarts))):
        result = _single_kmedoids(distance_matrix, rng.choice(n, size=k, replace=False))
        signature = (result["objective"], tuple(result["medoid_indices"].tolist()))
        if best is None or signature < best[0]:
            best = (signature, result)
    return best[1]


def majority_purity(cluster_ids, values):
    cluster_ids = list(cluster_ids)
    values = list(values)
    if not values:
        return 0.0
    correct = 0
    for cluster_id in sorted(set(cluster_ids)):
        cluster_values = [value for label, value in zip(cluster_ids, values) if label == cluster_id]
        correct += Counter(cluster_values).most_common(1)[0][1]
    return correct / len(values)


def select_member_audit_rows(fitted, records, distances, nearest_n=5, farthest_n=5):
    labels = np.asarray(fitted["labels"])
    medoids = set(int(value) for value in fitted["medoid_indices"])
    rows = []
    for cluster_id in sorted(set(labels.tolist())):
        members = np.flatnonzero(labels == cluster_id).tolist()
        medoid = next(index for index in members if index in medoids)
        ordered = sorted((index for index in members if index != medoid), key=lambda index: (distances[index, medoid], index))
        selected = [("nearest", index) for index in ordered[:nearest_n]]
        selected.extend(("boundary", index) for index in ordered[-farthest_n:])
        rows.append({"cluster_id": int(cluster_id), "kind": "medoid", "distance_to_medoid": 0.0, **records[medoid]})
        for kind, index in selected:
            rows.append({"cluster_id": int(cluster_id), "kind": kind, "distance_to_medoid": float(distances[index, medoid]), **records[index]})
    return rows


def search_k(config, embeddings, records):
    output = Path(config.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    distances = cosine_distance_matrix(embeddings)
    results = []
    fitted_by_k = {}
    for k in range(config.k_min, min(config.k_max, len(records) - 1) + 1):
        fitted = fit_kmedoids(distances, k, config.seed, config.random_restarts)
        labels = fitted["labels"]
        sizes = [int((labels == cluster_id).sum()) for cluster_id in range(k)]
        silhouette = float(silhouette_score(embeddings, labels, metric="cosine")) if len(set(labels.tolist())) > 1 else -1.0
        intra = [distances[index, fitted["medoid_indices"][labels[index]]] for index in range(len(labels))]
        metric = {
            "k": k, "silhouette": silhouette, "min_size": min(sizes), "max_size": max(sizes),
            "tiny_clusters": sum(size <= 3 for size in sizes), "giant_clusters": sum(size >= 50 for size in sizes),
            "mean_intra_cluster_distance": float(np.mean(intra)), "max_intra_cluster_distance": float(np.max(intra)),
            "relation_polarity_purity": majority_purity(labels, [row.get("relation_polarity") for row in records]),
            "conclusion_direction_purity": majority_purity(labels, [row.get("conclusion_direction") for row in records]),
            "premise_valence_purity": majority_purity(labels, [row.get("premise_valence") for row in records]),
        }
        results.append(metric)
        fitted_by_k[k] = fitted
    if not results:
        raise ValueError("k range produced no valid candidates")
    ranked = sorted(results, key=lambda row: (-row["silhouette"], row["giant_clusters"], row["tiny_clusters"], row["max_intra_cluster_distance"]))
    shortlist = [row["k"] for row in ranked[:3]]
    selected_k = shortlist[0]
    fitted = fitted_by_k[selected_k]
    with (output / "k_search_metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    assignments = []
    for index, record in enumerate(records):
        assignments.append({"sample_id": record["sample_id"] if "sample_id" in record else f"{record['article_id']}:{record['comment_id']}",
                            "cluster_id": int(fitted["labels"][index]), "medoid": int(fitted["medoid_indices"][fitted["labels"][index]])})
    with (output / "cluster_assignments.jsonl").open("w", encoding="utf-8") as stream:
        for row in assignments:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_json(output / "cluster_search.json", {"method": config.clustering_method, "seed": config.seed,
                                                   "selected_k": selected_k, "candidate_k": shortlist, "metrics": results})
    return {"selected_k": selected_k, "candidate_k": shortlist, "metrics": results, "fitted": fitted, "distances": distances}

