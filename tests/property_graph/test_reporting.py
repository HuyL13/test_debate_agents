from copy import deepcopy

from src.property_graph.reporting import diff_graphs, render_graph_diff
from src.property_graph.seed import build_seed_graph, load_definitions


def test_diff_reports_addition_and_edge_update():
    seed = build_seed_graph(load_definitions("definitions/fallacy_labels.json"), {})
    evolved = deepcopy(seed)
    evolved["nodes"].append({
        "id": "prototype:appeal_to_authority:001",
        "type": "prototype",
        "name": "Prototype",
        "attrs": {
            "source": "induced",
            "label": "appeal_to_authority",
            "required_features": ["REL:APPEALS_TO_SOURCE"],
            "typical_features": [],
            "support_count": 2,
            "source_sample_ids": ["s1", "s2"],
            "provenance": ["s1", "s2"],
        },
    })
    evolved["edges"][0]["weight"] = 0.75
    evolved["edges"][0]["support_count"] = 2

    diff = diff_graphs(seed, evolved)

    assert diff["added_nodes"][0]["id"] == "prototype:appeal_to_authority:001"
    assert diff["modified_edges"][0]["weight_delta"] == -0.25
    assert diff["modified_edges"][0]["support_count_delta"] == 2
    assert diff["locked_seed_invariants"]["violations"] == []
    assert "prototype:appeal_to_authority:001" in render_graph_diff(diff)
