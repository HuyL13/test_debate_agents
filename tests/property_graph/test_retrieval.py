from src.property_graph.indexing import build_indexes
from src.property_graph.induction import induce_cross_label, induce_within_label
from src.property_graph.retrieval import retrieval_metrics, retrieve
from src.property_graph.seed import build_seed_graph, load_definitions
from tests.property_graph.test_induction import config, record


def evolved_graph():
    seed = build_seed_graph(load_definitions("definitions/fallacy_labels.json"), {})
    records = [
        record("1", "Appeal to Authority", ["REL:USED_AS_JUSTIFICATION", "SOURCE_TYPE:expert"]),
        record("2", "Appeal to Majority", ["REL:USED_AS_JUSTIFICATION", "SOURCE_TYPE:majority"]),
    ]
    graph, _ = induce_within_label(seed, records, config(min_cluster_size=1))
    graph, _ = induce_cross_label(graph, records, {
        "min_shared_features": 1,
        "min_shared_support": 2,
        "discriminative_min_abs_score": 1.0,
        "discriminative_min_support": 1,
    })
    return graph


def test_retrieval_ranks_and_explains():
    graph = evolved_graph()
    signature = {"features": ["REL:USED_AS_JUSTIFICATION", "SOURCE_TYPE:expert"]}
    result = retrieve(signature, graph, build_indexes(graph), top_k_labels=2)

    top = result["candidate_labels"][0]
    assert top["label"] == "Appeal to Authority"
    assert top["matched_prototypes"] == ["prototype:appeal_to_authority:001"]
    assert top["missing_conditions"] == []
    assert "SOURCE_TYPE:expert" in top["matched_conditions"]
    assert top["score"] > result["candidate_labels"][1]["score"]


def test_metrics_reports_recall_and_mrr():
    rows = [
        {"gold": "A", "ranked_labels": ["B", "A", "C", "D"]},
        {"gold": "C", "ranked_labels": ["C", "A", "B", "D"]},
    ]
    metrics = retrieval_metrics(rows)
    assert metrics["recall_at_1"] == 0.5
    assert metrics["recall_at_2"] == 1.0
    assert metrics["recall_at_3"] == 1.0
    assert metrics["recall_at_4"] == 1.0
    assert metrics["mrr"] == 0.75
