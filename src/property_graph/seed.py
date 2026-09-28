"""Build a definition-initialized property graph."""

import json
from pathlib import Path

from src.labels import FALLACIES
from src.property_graph.schemas import slug, validate_graph


def load_definitions(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0" or not isinstance(payload.get("labels"), list):
        raise ValueError("invalid label definitions")
    names = [item.get("label") for item in payload["labels"]]
    if set(names) != set(FALLACIES) or len(names) != len(FALLACIES):
        raise ValueError("definitions must cover the eight CoCoLoFa labels exactly")
    return payload["labels"]


def build_seed_graph(definitions, meta):
    nodes = []
    edges = []
    for definition in definitions:
        label_name = definition["label"]
        label_slug = slug(label_name)
        label_id = f"label:{label_slug}"
        nodes.append({
            "id": label_id,
            "type": "label",
            "name": label_name,
            "attrs": {
                "source": "definition",
                "locked": True,
                "definition": definition["definition"],
            },
        })
        for mechanism in definition["mechanisms"]:
            mechanism_id = f"mechanism:{label_slug}:{slug(mechanism)}"
            nodes.append({
                "id": mechanism_id,
                "type": "abstract_mechanism",
                "name": mechanism,
                "attrs": {"source": "definition", "locked": False},
            })
            edges.append(_edge(label_id, mechanism_id, "HAS_MECHANISM"))
        for condition in definition["conditions"]:
            condition_id = f"condition:{label_slug}:{slug(condition)}"
            nodes.append({
                "id": condition_id,
                "type": "condition",
                "name": condition,
                "attrs": {"source": "definition", "locked": False},
            })
            edges.append(_edge(label_id, condition_id, "REQUIRES"))
    graph = {
        "meta": dict(meta),
        "nodes": sorted(nodes, key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: item["id"]),
    }
    return validate_graph(graph)


def _edge(source, target, edge_type):
    return {
        "id": f"edge:{slug(source)}:{edge_type.lower()}:{slug(target)}",
        "source": source,
        "target": target,
        "type": edge_type,
        "weight": 1.0,
        "support_count": 0,
        "attrs": {"source": "definition"},
        "provenance": [],
    }

