"""Deterministic within-label property-graph induction."""

from collections import Counter, defaultdict
from copy import deepcopy

from src.property_graph.schemas import slug, validate_graph


def _family(feature):
    prefix = feature.split(":", 1)[0]
    if prefix in {"REL", "ROLE", "EXPLICITNESS", "STRUCTURE"}:
        return "relations"
    if prefix in {"SOURCE_TYPE", "PROPERTY_TYPE", "ALTERNATIVES_COUNT"}:
        return "semantic"
    return "qualifiers"


def _jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def structural_similarity(left, right, weights):
    left_sets = defaultdict(set)
    right_sets = defaultdict(set)
    for feature in left:
        left_sets[_family(feature)].add(feature)
    for feature in right:
        right_sets[_family(feature)].add(feature)
    return sum(
        weights[family] * _jaccard(left_sets[family], right_sets[family])
        for family in ("relations", "semantic", "qualifiers")
    )


def cluster_signatures(records, threshold, min_cluster_size, weights):
    remaining = set(range(len(records)))
    components = []
    while remaining:
        root = min(remaining, key=lambda index: records[index]["sample_id"])
        remaining.remove(root)
        component = {root}
        frontier = [root]
        while frontier:
            current = frontier.pop()
            neighbors = []
            for other in remaining:
                distance = 1.0 - structural_similarity(
                    records[current]["features"], records[other]["features"], weights
                )
                if distance <= threshold:
                    neighbors.append(other)
            for other in neighbors:
                remaining.remove(other)
                component.add(other)
                frontier.append(other)
        components.append([records[index] for index in sorted(component, key=lambda i: records[i]["sample_id"])])
    clusters = [group for group in components if len(group) >= min_cluster_size]
    outliers = [item for group in components if len(group) < min_cluster_size for item in group]
    return clusters, sorted(outliers, key=lambda item: item["sample_id"])


def _medoids(cluster, weights, limit=3):
    ranked = []
    for candidate in cluster:
        distances = [
            1.0 - structural_similarity(candidate["features"], other["features"], weights)
            for other in cluster
        ]
        ranked.append((sum(distances) / len(distances), candidate["sample_id"]))
    return [sample_id for _, sample_id in sorted(ranked)[:limit]]


def induce_within_label(seed_graph, records, config):
    graph = deepcopy(seed_graph)
    by_label = defaultdict(list)
    for record in records:
        by_label[record["gold_label"]].append(record)
    audit = {}
    for label in sorted(by_label):
        label_records = sorted(by_label[label], key=lambda item: item["sample_id"])
        clusters, outliers = cluster_signatures(
            label_records,
            config["distance_threshold"],
            config["min_cluster_size"],
            config["similarity_weights"],
        )
        prototypes = []
        for cluster_index, cluster in enumerate(clusters, 1):
            counts = Counter(feature for record in cluster for feature in record["features"])
            size = len(cluster)
            required = sorted(
                feature for feature, count in counts.items()
                if count / size >= config["required_feature_ratio"]
            )
            typical = sorted(
                feature for feature, count in counts.items()
                if config["typical_feature_ratio"] <= count / size < config["required_feature_ratio"]
            )
            variants = sorted(
                feature for feature, count in counts.items()
                if count / size < config["typical_feature_ratio"]
            )
            label_slug = slug(label)
            prototype_id = f"prototype:{label_slug}:{cluster_index:03d}"
            provenance = sorted(record["sample_id"] for record in cluster)
            node = {
                "id": prototype_id,
                "type": "prototype",
                "name": f"{label} prototype {cluster_index:03d}",
                "attrs": {
                    "source": "induced",
                    "label": label_slug,
                    "required_features": required,
                    "typical_features": typical,
                    "variant_features": variants,
                    "support_count": size,
                    "source_sample_ids": provenance,
                    "representative_sample_ids": _medoids(cluster, config["similarity_weights"]),
                    "cluster_id": cluster_index,
                    "provenance": provenance,
                    "induction_config": {
                        "distance_threshold": config["distance_threshold"],
                        "required_feature_ratio": config["required_feature_ratio"],
                        "typical_feature_ratio": config["typical_feature_ratio"],
                    },
                },
            }
            edge = {
                "id": f"edge:label_{label_slug}:has_prototype:{slug(prototype_id)}",
                "source": f"label:{label_slug}",
                "target": prototype_id,
                "type": "HAS_PROTOTYPE",
                "weight": 1.0,
                "support_count": size,
                "attrs": {"source": "induced"},
                "provenance": provenance,
            }
            graph["nodes"].append(node)
            graph["edges"].append(edge)
            prototypes.append(prototype_id)
        audit[label] = {
            "sample_count": len(label_records),
            "prototype_ids": prototypes,
            "outlier_sample_ids": [item["sample_id"] for item in outliers],
            "outlier_ratio": len(outliers) / len(label_records),
        }
    graph["nodes"].sort(key=lambda item: item["id"])
    graph["edges"].sort(key=lambda item: item["id"])
    return validate_graph(graph), audit


def induce_cross_label(graph, records, config):
    graph = deepcopy(graph)
    prototypes = [node for node in graph["nodes"] if node["type"] == "prototype"]
    by_label = defaultdict(list)
    for record in records:
        by_label[slug(record["gold_label"])].append(record)
    shared_ids = []
    discriminative_ids = []
    seen_shared = set()
    seen_conditions = set()

    for index, left in enumerate(prototypes):
        for right in prototypes[index + 1:]:
            left_label = left["attrs"]["label"]
            right_label = right["attrs"]["label"]
            if left_label == right_label:
                continue
            common = sorted(
                set(left["attrs"]["required_features"]) & set(right["attrs"]["required_features"])
            )
            provenance = sorted(set(left["attrs"]["source_sample_ids"]) | set(right["attrs"]["source_sample_ids"]))
            if len(common) >= config["min_shared_features"] and len(provenance) >= config["min_shared_support"]:
                labels = sorted((left_label, right_label))
                shared_id = f"shared_mechanism:{slug('|'.join(common))}:{':'.join(labels)}"
                if shared_id not in seen_shared:
                    seen_shared.add(shared_id)
                    graph["nodes"].append({
                        "id": shared_id,
                        "type": "shared_mechanism",
                        "name": "Shared structural mechanism: " + ", ".join(common),
                        "attrs": {
                            "source": "induced",
                            "shared_by_labels": labels,
                            "core_features": common,
                            "support_count": len(provenance),
                            "provenance": provenance,
                        },
                    })
                    for label in labels:
                        graph["edges"].append({
                            "id": f"edge:label_{label}:shares:{slug(shared_id)}",
                            "source": f"label:{label}",
                            "target": shared_id,
                            "type": "SHARES_MECHANISM",
                            "weight": 1.0,
                            "support_count": len(provenance),
                            "attrs": {"source": "induced"},
                            "provenance": provenance,
                        })
                    shared_ids.append(shared_id)
                _add_discriminative_conditions(
                    graph, by_label, left_label, right_label, config,
                    seen_conditions, discriminative_ids,
                )

    graph["nodes"].sort(key=lambda item: item["id"])
    graph["edges"].sort(key=lambda item: item["id"])
    return validate_graph(graph), {
        "shared_mechanisms": sorted(shared_ids),
        "discriminative_conditions": sorted(discriminative_ids),
    }


def _add_discriminative_conditions(
    graph, by_label, left_label, right_label, config, seen_conditions, result_ids
):
    import math

    left_records = by_label[left_label]
    right_records = by_label[right_label]
    features = sorted({
        feature for record in left_records + right_records for feature in record["features"]
    })
    for feature in features:
        left_count = sum(feature in record["features"] for record in left_records)
        right_count = sum(feature in record["features"] for record in right_records)
        if left_count + right_count < config["discriminative_min_support"]:
            continue
        left_odds = (left_count + 0.5) / (len(left_records) - left_count + 0.5)
        right_odds = (right_count + 0.5) / (len(right_records) - right_count + 0.5)
        score = math.log(left_odds) - math.log(right_odds)
        if abs(score) < config["discriminative_min_abs_score"]:
            continue
        owner, contrast = (left_label, right_label) if score > 0 else (right_label, left_label)
        condition_id = f"condition:induced:{owner}:{slug(feature)}:vs:{contrast}"
        if condition_id in seen_conditions:
            continue
        seen_conditions.add(condition_id)
        owner_records = by_label[owner]
        provenance = sorted(
            record["sample_id"] for record in owner_records if feature in record["features"]
        )
        graph["nodes"].append({
            "id": condition_id,
            "type": "condition",
            "name": f"{feature} distinguishes {owner} from {contrast}",
            "attrs": {
                "source": "induced",
                "feature": feature,
                "label": owner,
                "contrast_label": contrast,
                "statistic": "smoothed_log_odds",
                "score": abs(score),
                "support_count": len(provenance),
                "provenance": provenance,
            },
        })
        graph["edges"].append({
            "id": f"edge:label_{owner}:differs_by:{slug(condition_id)}",
            "source": f"label:{owner}",
            "target": condition_id,
            "type": "DIFFERS_BY",
            "weight": min(1.0, abs(score) / 4.0),
            "support_count": len(provenance),
            "attrs": {
                "source": "induced",
                "contrast_label": contrast,
                "statistic": "smoothed_log_odds",
            },
            "provenance": provenance,
        })
        result_ids.append(condition_id)


