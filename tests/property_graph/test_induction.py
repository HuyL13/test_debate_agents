from src.property_graph.induction import (
    induce_cross_label,
    induce_within_label,
    structural_similarity,
)
from src.property_graph.seed import build_seed_graph, load_definitions


def record(sample_id, label, features):
    return {"sample_id": sample_id, "gold_label": label, "features": sorted(features)}


def config(min_cluster_size=2):
    return {
        "similarity_weights": {"relations": 0.5, "semantic": 0.35, "qualifiers": 0.15},
        "distance_threshold": 0.2,
        "min_cluster_size": min_cluster_size,
        "required_feature_ratio": 0.8,
        "typical_feature_ratio": 0.4,
    }


def test_structural_similarity_weights_feature_families():
    left = ["REL:SUPPORTS", "SOURCE_TYPE:expert", "QUALIFIER:universal"]
    right = ["REL:SUPPORTS", "SOURCE_TYPE:majority", "QUALIFIER:universal"]
    assert structural_similarity(left, right, config()["similarity_weights"]) == 0.65


def test_within_label_has_provenance_and_outlier():
    seed = build_seed_graph(load_definitions("definitions/fallacy_labels.json"), {})
    records = [
        record("1", "Appeal to Authority", ["REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert"]),
        record("2", "Appeal to Authority", ["REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert"]),
        record("3", "Appeal to Authority", ["REL:ATTACKS"]),
    ]
    graph, audit = induce_within_label(seed, records, config())
    prototype = next(node for node in graph["nodes"] if node["type"] == "prototype")
    assert prototype["attrs"]["required_features"] == [
        "REL:APPEALS_TO_SOURCE", "SOURCE_TYPE:expert",
    ]
    assert prototype["attrs"]["source_sample_ids"] == ["1", "2"]
    assert prototype["attrs"]["representative_sample_ids"] == ["1", "2"]
    assert audit["Appeal to Authority"]["outlier_sample_ids"] == ["3"]


def test_cross_label_adds_shared_and_discriminative_nodes():
    seed = build_seed_graph(load_definitions("definitions/fallacy_labels.json"), {})
    records = [
        record("1", "Appeal to Authority", ["REL:USED_AS_JUSTIFICATION", "SOURCE_TYPE:expert"]),
        record("2", "Appeal to Majority", ["REL:USED_AS_JUSTIFICATION", "SOURCE_TYPE:majority"]),
    ]
    prototype_graph, _ = induce_within_label(seed, records, config(min_cluster_size=1))
    graph, audit = induce_cross_label(prototype_graph, records, {
        "min_shared_features": 1,
        "min_shared_support": 2,
        "discriminative_min_abs_score": 1.0,
        "discriminative_min_support": 1,
    })
    shared = [node for node in graph["nodes"] if node["type"] == "shared_mechanism"]
    assert shared[0]["attrs"]["shared_by_labels"] == [
        "appeal_to_authority", "appeal_to_majority",
    ]
    assert shared[0]["attrs"]["provenance"] == ["1", "2"]
    assert any(edge["type"] == "DIFFERS_BY" for edge in graph["edges"])
    assert audit["shared_mechanisms"] == [shared[0]["id"]]
