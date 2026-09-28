from src.labels import FALLACIES
from src.property_graph.graph_io import get_label_subgraph, load_graph, save_graph
from src.property_graph.seed import build_seed_graph, load_definitions


def test_seed_has_locked_labels_and_round_trips(tmp_path):
    graph = build_seed_graph(
        load_definitions("definitions/fallacy_labels.json"),
        {"graph_version": "seed"},
    )
    labels = [node for node in graph["nodes"] if node["type"] == "label"]
    assert {node["name"] for node in labels} == set(FALLACIES)
    assert all(node["attrs"]["locked"] is True for node in labels)

    path = tmp_path / "seed.json"
    save_graph(graph, path)
    assert load_graph(path) == graph


def test_label_subgraph_contains_definition_neighbors():
    graph = build_seed_graph(load_definitions("definitions/fallacy_labels.json"), {})
    subgraph = get_label_subgraph(graph, "label:appeal_to_authority")
    assert {node["type"] for node in subgraph["nodes"]} >= {
        "label", "abstract_mechanism", "condition",
    }
    assert all(
        edge["source"] == "label:appeal_to_authority"
        or edge["target"] == "label:appeal_to_authority"
        for edge in subgraph["edges"]
    )
