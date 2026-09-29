import json
import os
from pathlib import Path

from src.induction.contracts import (
    cluster_audit_schema,
    cluster_mode_schema,
    merge_plan_schema,
    validate_cluster_audit,
    validate_cluster_mode,
    validate_merge_plan,
)
from src.induction.prompts import cluster_audit_prompt, cluster_mode_prompt, merge_prompt
from src.io_utils import append_jsonl, read_jsonl, write_json


def _client(config):
    from src.llm.client import Client
    from src.llm.config import ModelConfig
    model = os.environ.get(config.model_env, "configured-model")
    return Client(ModelConfig(name=model, temperature=config.llm_temperature,
                              max_attempts=config.llm_max_retries),
                  Path(config.output_dir) / "llm_cache.sqlite3",
                  Path(config.output_dir) / "audit" / "api_calls.jsonl")


def _gate(config):
    path = Path(config.output_dir) / "cluster_gate.json"
    if not path.exists() or not json.loads(path.read_text(encoding="utf-8")).get("passed"):
        raise RuntimeError("cluster audit has not passed")


def render_induced_definition(label, modes, provenance):
    lines = [f"# Induced Definition — {label}", "", "## 1. Core invariant", "", "The central invariant must be supported by the audited modes below.", "", "## 2. Prototypical inferential relation", "", "PREMISE", "→ BRIDGE", "→ CONCLUSION", "", "## 3. Discovered reasoning modes", ""]
    for index, mode in enumerate(modes, 1):
        lines.extend([
            f"### Mode {index} — {mode['mode_name']}",
            f"Cluster {mode['cluster_id']}",
            f"Coverage: {mode['coverage_n']}",
            f"Relation: {mode['canonical_template']}",
            f"Representative member IDs: {', '.join(mode['supporting_member_ids'])}",
            "",
        ])
    lines.extend(["## 4. Boundary conditions", "", "### Not sufficient", "", "Only the audited inferential relation is sufficient; topic words alone are not.", "", "### Opposite-direction cases", "", "Opposite directions remain separate during audit.", "", "### Descriptive / non-inferential cases", "", "Descriptive history without an inferential bridge is not sufficient.", "", "## 5. Dataset-edge / noisy modes", "", "See the audited cluster notes.", "", "## 6. Operational classification test", "", "1. Identify the premise and conclusion.", "2. Identify the bridge connecting them.", "3. Check whether that bridge matches an audited mode.", "", "## 7. Provenance", ""])
    for key, value in provenance.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def audit_clusters(config, client=None):
    output = Path(config.output_dir)
    assignments = read_jsonl(output / "cluster_assignments.jsonl")
    records = {row["sample_id"]: row for row in read_jsonl(output / "semantic_records.jsonl")}
    clusters = {}
    for assignment in assignments:
        clusters.setdefault(assignment["cluster_id"], []).append(records[assignment["sample_id"]])
    client = client or _client(config)
    audits = []
    for cluster_id, members in sorted(clusters.items()):
        medoid_id = next(row["sample_id"] for row in assignments if row["cluster_id"] == cluster_id and row["sample_id"] == row.get("medoid_sample_id", row["sample_id"]))
        payload = {"cluster_id": cluster_id, "size": len(members), "medoid": next(row for row in members if row["sample_id"] == medoid_id), "members": members}
        system, user = cluster_audit_prompt(payload)
        result = client.generate(system_prompt=system, user_prompt=user, schema=cluster_audit_schema(),
                                 metadata={"stage": "cluster_audit", "cluster_id": cluster_id},
                                 validator=validate_cluster_audit)
        audits.append(result.output)
        append_jsonl(output / "cluster_audits.jsonl", result.output)
    passed = bool(audits) and not any(row["member_consistency"] == "LOW" and row["medoid_representative"] == "NO" for row in audits)
    write_json(output / "cluster_gate.json", {"passed": passed, "cluster_count": len(audits), "audits": audits})
    (output / "cluster_member_audit.md").write_text("# Cluster Member Audit\n\n" + "\n".join(f"- Cluster {row['cluster_id']}: {row['member_consistency']} / {row['medoid_representative']}" for row in audits) + "\n", encoding="utf-8")
    return {"passed": passed, "audits": audits}


def induce_cluster_modes(config, client=None):
    _gate(config)
    output = Path(config.output_dir)
    audits = read_jsonl(output / "cluster_audits.jsonl")
    client = client or _client(config)
    modes = []
    for audit in audits:
        system, user = cluster_mode_prompt(audit)
        result = client.generate(system_prompt=system, user_prompt=user, schema=cluster_mode_schema(),
                                 metadata={"stage": "cluster_mode_induction", "cluster_id": audit["cluster_id"]},
                                 validator=validate_cluster_mode)
        modes.append(result.output)
        append_jsonl(output / "cluster_modes.jsonl", result.output)
    return modes


def merge_cluster_modes(config, modes, client=None):
    client = client or _client(config)
    system, user = merge_prompt(modes)
    result = client.generate(system_prompt=system, user_prompt=user, schema=merge_plan_schema(),
                             metadata={"stage": "mode_merge"}, validator=validate_merge_plan)
    write_json(Path(config.output_dir) / "mode_merge_plan.json", result.output)
    return result.output


def induce_definition(config, client=None):
    _gate(config)
    output = Path(config.output_dir)
    modes = read_jsonl(output / "cluster_modes.jsonl")
    provenance = json.loads((output / "run_manifest.json").read_text(encoding="utf-8")) if (output / "run_manifest.json").exists() else {"sample_count": len(read_jsonl(output / "semantic_records.jsonl"))}
    text = render_induced_definition(config.label, modes, provenance)
    (output / "induced_definition.md").write_text(text, encoding="utf-8")
    return {"path": str(output / "induced_definition.md"), "status": "PARTIALLY READY"}

