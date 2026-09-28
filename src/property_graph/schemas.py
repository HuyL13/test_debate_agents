"""Schemas and semantic validation for property-graph induction."""

import math
import re

from src.schemas import validate_output


SIGNATURE_SCHEMA_VERSION = "1.0"
PROPOSITION_ROLES = (
    "premise", "conclusion", "intermediate_conclusion", "example",
    "counterclaim", "quoted_claim", "background", "unknown",
)
SPEAKER_ROLES = ("target", "parent", "quoted_external_source", "unknown")
RELATION_TYPES = (
    "SUPPORTS", "ATTACKS", "USED_AS_JUSTIFICATION", "GENERALIZES_TO",
    "CAUSES", "TEMPORALLY_PRECEDES", "CONDITIONS", "COMPARES_TO",
    "RESTRICTS_ALTERNATIVES", "APPEALS_TO_SOURCE", "APPEALS_TO_PROPERTY",
    "LEADS_TO", "DISMISSES_BY_COMPARISON",
)
SOURCE_TYPES = (
    "expert", "authority_status", "institution", "majority", "tradition",
    "nature", "individual", "small_group", "unspecified",
)
SCOPES = ("individual", "subgroup", "population", "universal", "unspecified")
PROPERTY_TYPES = (
    "expertise", "popularity", "tradition", "naturalness", "severity",
    "consequence", "unspecified",
)
NODE_TYPES = (
    "label", "abstract_mechanism", "condition", "relation_type",
    "prototype", "shared_mechanism", "train_example",
)
EDGE_TYPES = (
    "HAS_MECHANISM", "HAS_PROTOTYPE", "REQUIRES", "TYPICALLY_HAS",
    "SHARES_MECHANISM", "DIFFERS_BY", "CONTRADICTS", "SUPPORTED_BY",
)


def _nullable(values):
    return {"anyOf": [{"type": "string", "enum": list(values)}, {"type": "null"}]}


SIGNATURE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "sample_id", "propositions", "relations", "semantic_roles",
        "qualifiers", "structural_features", "uncertainties",
    ],
    "properties": {
        "sample_id": {"type": "string", "minLength": 1},
        "propositions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text", "speaker", "role"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "text": {"type": "string", "minLength": 1},
                    "speaker": {"type": "string", "enum": list(SPEAKER_ROLES)},
                    "role": {"type": "string", "enum": list(PROPOSITION_ROLES)},
                },
            },
        },
        "relations": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source", "target", "type", "status", "explicitness",
                    "evidence_spans",
                ],
                "properties": {
                    "source": {"type": "string", "minLength": 1},
                    "target": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "enum": list(RELATION_TYPES)},
                    "status": {"type": "string", "enum": ["asserted", "uncertain"]},
                    "explicitness": {"type": "string", "enum": ["explicit", "implicit", "uncertain"]},
                    "evidence_spans": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "semantic_roles": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "source_type", "sample_scope", "target_scope",
                "alternatives_count", "property_type", "comparison_target",
            ],
            "properties": {
                "source_type": _nullable(SOURCE_TYPES),
                "sample_scope": _nullable(SCOPES),
                "target_scope": _nullable(SCOPES),
                "alternatives_count": {
                    "anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}],
                },
                "property_type": _nullable(PROPERTY_TYPES),
                "comparison_target": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
            },
        },
        "qualifiers": {
            "type": "object",
            "additionalProperties": False,
            "required": ["certainty", "universality", "normative"],
            "properties": {
                "certainty": _nullable(("low", "medium", "high", "unspecified")),
                "universality": _nullable(("limited", "broad", "universal", "unspecified")),
                "normative": {"type": "boolean"},
            },
        },
        "structural_features": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "premise_to_conclusion", "implicit_justification",
                    "explicit_justification", "scope_shift", "source_endorsement",
                    "restricted_alternatives", "causal_chain", "comparison_dismissal",
                ],
            },
        },
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
}


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def validate_signature(signature, visible_text):
    validate_output(signature, SIGNATURE_JSON_SCHEMA)
    proposition_ids = [item["id"] for item in signature["propositions"]]
    if len(proposition_ids) != len(set(proposition_ids)):
        raise ValueError("duplicate proposition id")
    known = set(proposition_ids)
    for relation in signature["relations"]:
        if relation["source"] not in known or relation["target"] not in known:
            raise ValueError("relation endpoint does not exist")
        for span in relation["evidence_spans"]:
            if span not in visible_text:
                raise ValueError("evidence span is not present in visible text")
    return signature


def validate_graph(graph):
    if not isinstance(graph, dict) or set(graph) != {"meta", "nodes", "edges"}:
        raise ValueError("graph must contain exactly meta, nodes, and edges")
    if not isinstance(graph["meta"], dict) or not isinstance(graph["nodes"], list) or not isinstance(graph["edges"], list):
        raise ValueError("invalid graph container")

    node_ids = []
    for node in graph["nodes"]:
        required = {"id", "type", "name", "attrs"}
        if not isinstance(node, dict) or set(node) != required:
            raise ValueError("invalid graph node")
        if node["type"] not in NODE_TYPES:
            raise ValueError("unsupported node type")
        if not isinstance(node["id"], str) or not node["id"] or not isinstance(node["name"], str):
            raise ValueError("invalid node identity")
        if not isinstance(node["attrs"], dict):
            raise ValueError("invalid node attrs")
        if node["type"] == "label" and node["attrs"].get("locked") is not True:
            raise ValueError("label nodes must be locked")
        if node["attrs"].get("source") == "induced" and not (
            node["attrs"].get("provenance") or node["attrs"].get("source_sample_ids")
        ):
            raise ValueError("induced node requires provenance")
        node_ids.append(node["id"])
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("duplicate node id")

    known = set(node_ids)
    edge_ids = []
    for edge in graph["edges"]:
        required = {"id", "source", "target", "type", "weight", "support_count", "attrs", "provenance"}
        if not isinstance(edge, dict) or set(edge) != required:
            raise ValueError("invalid graph edge")
        if edge["type"] not in EDGE_TYPES:
            raise ValueError("unsupported edge type")
        if edge["source"] not in known or edge["target"] not in known:
            raise ValueError("edge endpoint does not exist")
        if type(edge["weight"]) not in (int, float) or not math.isfinite(edge["weight"]):
            raise ValueError("edge weight must be finite")
        if type(edge["support_count"]) is not int or edge["support_count"] < 0:
            raise ValueError("edge support_count must be non-negative")
        if not isinstance(edge["attrs"], dict) or not isinstance(edge["provenance"], list):
            raise ValueError("invalid edge metadata")
        if edge["attrs"].get("source") == "induced" and not edge["provenance"]:
            raise ValueError("induced edge requires provenance")
        edge_ids.append(edge["id"])
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError("duplicate edge id")
    return graph

