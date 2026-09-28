"""Validated JSON persistence and graph navigation."""

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

from src.property_graph.schemas import validate_graph


def load_graph(path):
    graph = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_graph(graph)


def save_graph(graph, path):
    validate_graph(graph)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(graph, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def build_node_map(graph):
    validate_graph(graph)
    return {node["id"]: node for node in graph["nodes"]}


def build_adjacency(graph):
    validate_graph(graph)
    adjacency = defaultdict(list)
    for edge in graph["edges"]:
        adjacency[edge["source"]].append(edge)
        adjacency[edge["target"]].append(edge)
    return {key: sorted(value, key=lambda edge: edge["id"]) for key, value in adjacency.items()}


def get_neighbors(graph, node_id, edge_types=None):
    if node_id not in build_node_map(graph):
        raise KeyError(node_id)
    allowed = set(edge_types) if edge_types is not None else None
    return [
        edge for edge in graph["edges"]
        if (edge["source"] == node_id or edge["target"] == node_id)
        and (allowed is None or edge["type"] in allowed)
    ]


def get_label_subgraph(graph, label_id):
    node_map = build_node_map(graph)
    label = node_map.get(label_id)
    if label is None or label["type"] != "label":
        raise KeyError(label_id)
    edges = get_neighbors(graph, label_id)
    node_ids = {label_id}
    for edge in edges:
        node_ids.update((edge["source"], edge["target"]))
    return {
        "meta": dict(graph["meta"]),
        "nodes": [node_map[node_id] for node_id in sorted(node_ids)],
        "edges": sorted(edges, key=lambda edge: edge["id"]),
    }

