"""LLM-free retrieval over induced property-graph prototypes."""

from collections import defaultdict


DEFAULT_WEIGHTS = {
    "required_coverage": 0.50,
    "jaccard": 0.25,
    "typical_coverage": 0.15,
    "discriminative_bonus": 0.10,
}


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else 1.0


def _jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def retrieve(
    signature,
    graph,
    indexes,
    top_k_labels=4,
    top_k_prototypes=8,
    weights=None,
):
    weights = weights or DEFAULT_WEIGHTS
    query = set(signature["features"])
    node_map = {node["id"]: node for node in graph["nodes"]}
    candidates = {
        node_id
        for feature in query
        for node_id in indexes["feature_to_nodes"].get(feature, [])
    }
    prototype_rows = []
    for node_id in sorted(candidates):
        node = node_map[node_id]
        attrs = node["attrs"]
        required = set(attrs.get("required_features", []))
        typical = set(attrs.get("typical_features", []))
        label = attrs["label"]
        discriminative = {
            item["attrs"]["feature"]
            for item in graph["nodes"]
            if item["type"] == "condition"
            and item["attrs"].get("source") == "induced"
            and item["attrs"].get("label") == label
        }
        required_coverage = _ratio(len(query & required), len(required))
        typical_coverage = _ratio(len(query & typical), len(typical)) if typical else 0.0
        discriminative_bonus = 1.0 if query & discriminative else 0.0
        score = (
            weights["required_coverage"] * required_coverage
            + weights["jaccard"] * _jaccard(query, required | typical)
            + weights["typical_coverage"] * typical_coverage
            + weights["discriminative_bonus"] * discriminative_bonus
        )
        prototype_rows.append({
            "id": node_id,
            "label": label,
            "score": score,
            "matched": sorted(query & (required | typical | discriminative)),
            "missing": sorted(required - query),
            "representative_examples": attrs.get("representative_sample_ids", []),
        })
    prototype_rows.sort(key=lambda row: (-row["score"], row["label"], row["id"]))
    prototype_rows = prototype_rows[:top_k_prototypes]

    by_label = defaultdict(list)
    for row in prototype_rows:
        by_label[row["label"]].append(row)
    label_names = {
        node["id"].split(":", 1)[1]: node["name"]
        for node in graph["nodes"] if node["type"] == "label"
    }
    candidate_labels = []
    for label, rows in by_label.items():
        best = rows[0]
        shared = [
            node["id"] for node in graph["nodes"]
            if node["type"] == "shared_mechanism" and label in node["attrs"].get("shared_by_labels", [])
        ]
        differs = {
            node["attrs"]["contrast_label"]: node["attrs"]["feature"]
            for node in graph["nodes"]
            if node["type"] == "condition"
            and node["attrs"].get("source") == "induced"
            and node["attrs"].get("label") == label
        }
        candidate_labels.append({
            "label": label_names.get(label, label),
            "label_id": label,
            "score": best["score"],
            "matched_prototypes": [row["id"] for row in rows],
            "shared_mechanisms": sorted(shared),
            "matched_conditions": sorted(set().union(*(set(row["matched"]) for row in rows))),
            "missing_conditions": best["missing"],
            "contradicting_conditions": [],
            "differs_by": dict(sorted(differs.items())),
            "representative_examples": sorted(set(
                example for row in rows for example in row["representative_examples"]
            )),
        })
    candidate_labels.sort(key=lambda row: (-row["score"], row["label"]))
    return {
        "query_features": sorted(query),
        "candidate_labels": candidate_labels[:top_k_labels],
    }


def retrieval_metrics(rows):
    rows = list(rows)
    if not rows:
        raise ValueError("retrieval metrics require at least one row")
    metrics = {}
    for cutoff in range(1, 5):
        metrics[f"recall_at_{cutoff}"] = sum(
            row["gold"] in row["ranked_labels"][:cutoff] for row in rows
        ) / len(rows)
    reciprocal = []
    for row in rows:
        try:
            reciprocal.append(1.0 / (row["ranked_labels"].index(row["gold"]) + 1))
        except ValueError:
            reciprocal.append(0.0)
    metrics["mrr"] = sum(reciprocal) / len(reciprocal)
    return metrics

