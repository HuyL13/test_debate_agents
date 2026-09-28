"""Audit and seed-to-evolved graph comparison."""

from collections import Counter


def _counts(items):
    return dict(sorted(Counter(item["type"] for item in items).items()))


def diff_graphs(seed, evolved, audit=None):
    seed_nodes = {item["id"]: item for item in seed["nodes"]}
    evolved_nodes = {item["id"]: item for item in evolved["nodes"]}
    seed_edges = {item["id"]: item for item in seed["edges"]}
    evolved_edges = {item["id"]: item for item in evolved["edges"]}

    added_nodes = [evolved_nodes[key] for key in sorted(evolved_nodes.keys() - seed_nodes.keys())]
    removed_nodes = [seed_nodes[key] for key in sorted(seed_nodes.keys() - evolved_nodes.keys())]
    added_edges = [evolved_edges[key] for key in sorted(evolved_edges.keys() - seed_edges.keys())]
    removed_edges = [seed_edges[key] for key in sorted(seed_edges.keys() - evolved_edges.keys())]
    modified_nodes = [
        {"id": key, "before": seed_nodes[key], "after": evolved_nodes[key]}
        for key in sorted(seed_nodes.keys() & evolved_nodes.keys())
        if seed_nodes[key] != evolved_nodes[key]
    ]
    modified_edges = []
    for key in sorted(seed_edges.keys() & evolved_edges.keys()):
        before, after = seed_edges[key], evolved_edges[key]
        if before != after:
            modified_edges.append({
                "id": key,
                "before": before,
                "after": after,
                "weight_delta": after["weight"] - before["weight"],
                "support_count_delta": after["support_count"] - before["support_count"],
            })

    violations = []
    locked = [node for node in seed["nodes"] if node["type"] == "label" and node["attrs"].get("locked")]
    for node in locked:
        if evolved_nodes.get(node["id"]) != node:
            violations.append(node["id"])

    return {
        "totals": {
            "nodes": {"seed": len(seed["nodes"]), "evolved": len(evolved["nodes"])},
            "edges": {"seed": len(seed["edges"]), "evolved": len(evolved["edges"])},
            "seed_nodes_by_type": _counts(seed["nodes"]),
            "evolved_nodes_by_type": _counts(evolved["nodes"]),
            "seed_edges_by_type": _counts(seed["edges"]),
            "evolved_edges_by_type": _counts(evolved["edges"]),
        },
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "modified_nodes": modified_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "modified_edges": modified_edges,
        "prototypes_by_label": _prototype_summary(added_nodes),
        "shared_mechanisms": [n for n in added_nodes if n["type"] == "shared_mechanism"],
        "discriminative_conditions": [
            n for n in added_nodes
            if n["type"] == "condition" and n["attrs"].get("source") == "induced"
        ],
        "outliers": audit or {},
        "locked_seed_invariants": {
            "unchanged": sorted(node["id"] for node in locked if node["id"] not in violations),
            "violations": violations,
        },
    }


def _prototype_summary(nodes):
    result = {}
    for node in nodes:
        if node["type"] == "prototype":
            result.setdefault(node["attrs"]["label"], []).append({
                "id": node["id"],
                "required_features": node["attrs"].get("required_features", []),
                "typical_features": node["attrs"].get("typical_features", []),
                "support_count": node["attrs"].get("support_count", 0),
                "provenance": node["attrs"].get("provenance", []),
            })
    return dict(sorted(result.items()))


def render_graph_diff(diff):
    totals = diff["totals"]
    lines = [
        "# Seed-to-Evolved Graph Diff",
        "",
        f"- Nodes: {totals['nodes']['seed']} -> {totals['nodes']['evolved']}",
        f"- Edges: {totals['edges']['seed']} -> {totals['edges']['evolved']}",
        f"- Locked seed invariant violations: {len(diff['locked_seed_invariants']['violations'])}",
        "",
        "## Added nodes",
        "",
    ]
    lines.extend(
        f"- {node['id']} ({node['type']}), provenance: "
        + ", ".join(node["attrs"].get("provenance", node["attrs"].get("source_sample_ids", [])))
        for node in diff["added_nodes"]
    )
    if not diff["added_nodes"]:
        lines.append("- None")
    lines.extend(["", "## Modified edges", ""])
    lines.extend(
        f"- {edge['id']}: weight {edge['weight_delta']:+.4f}, "
        f"support {edge['support_count_delta']:+d}"
        for edge in diff["modified_edges"]
    )
    if not diff["modified_edges"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def render_induction_audit(audit):
    lines = ["# Graph Induction Audit", ""]
    for label, values in sorted(audit.get("within_label", {}).items()):
        lines.extend([
            f"## {label}",
            f"- Samples: {values['sample_count']}",
            f"- Prototypes: {len(values['prototype_ids'])}",
            f"- Outlier ratio: {values['outlier_ratio']:.3f}",
            "",
        ])
    cross = audit.get("cross_label", {})
    lines.extend([
        "## Cross-label",
        f"- Shared mechanisms: {len(cross.get('shared_mechanisms', []))}",
        f"- Discriminative conditions: {len(cross.get('discriminative_conditions', []))}",
        "",
    ])
    return "\n".join(lines)

