"""Deterministic inverted indexes for property graphs."""

import json
from pathlib import Path

from src.io_utils import write_json


INDEX_FILES = {
    "feature_to_nodes": "feature_to_nodes.json",
    "label_to_nodes": "label_to_nodes.json",
    "mechanism_to_examples": "mechanism_to_examples.json",
}


def build_indexes(graph):
    feature_to_nodes = {}
    label_to_nodes = {}
    mechanism_to_examples = {}
    for node in graph["nodes"]:
        attrs = node["attrs"]
        if node["type"] == "prototype":
            for feature in attrs.get("required_features", []) + attrs.get("typical_features", []):
                feature_to_nodes.setdefault(feature, []).append(node["id"])
            label_to_nodes.setdefault(attrs["label"], []).append(node["id"])
            mechanism_to_examples[node["id"]] = list(attrs.get("representative_sample_ids", []))
        elif node["type"] in {"shared_mechanism", "condition"} and attrs.get("source") == "induced":
            for label in attrs.get("shared_by_labels", [attrs.get("label")]):
                if label:
                    label_to_nodes.setdefault(label, []).append(node["id"])
            mechanism_to_examples[node["id"]] = list(attrs.get("provenance", []))
    return {
        "feature_to_nodes": {key: sorted(set(value)) for key, value in sorted(feature_to_nodes.items())},
        "label_to_nodes": {key: sorted(set(value)) for key, value in sorted(label_to_nodes.items())},
        "mechanism_to_examples": dict(sorted(mechanism_to_examples.items())),
    }


def save_indexes(indexes, directory):
    directory = Path(directory)
    for name, filename in INDEX_FILES.items():
        write_json(directory / filename, indexes[name])


def load_indexes(directory):
    directory = Path(directory)
    return {
        name: json.loads((directory / filename).read_text(encoding="utf-8"))
        for name, filename in INDEX_FILES.items()
    }

