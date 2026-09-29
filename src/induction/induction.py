import json
import os
from pathlib import Path

from src.induction.contracts import (
    cluster_audit_schema,
    cluster_mode_schema,
    final_definition_schema,
    merge_plan_schema,
    validate_cluster_audit,
    validate_cluster_mode,
    validate_final_definition,
    validate_merge_plan,
)
from src.induction.prompts import cluster_audit_prompt, cluster_mode_prompt, final_definition_prompt, merge_prompt
from src.io_utils import append_jsonl, read_jsonl, write_json


def _client(config):
    from src.llm.client import Client
    from src.llm.config import ModelConfig
    model = os.environ.get(config.model_env, "configured-model")
    base_url = os.environ.get(config.base_url_env, "https://api.openai.com/v1")
    model_config = ModelConfig(name=model, base_url=base_url, api_key_env=config.api_key_env,
                               provider="openai_compatible" if base_url != "https://api.openai.com/v1" else "openai",
                               temperature=config.llm_temperature, max_attempts=config.llm_max_retries)
    return Client(model_config,
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
    member_audit_rows = []
    for cluster_id, members in sorted(clusters.items()):
        medoid_id = next(row["sample_id"] for row in assignments if row["cluster_id"] == cluster_id and row["sample_id"] == row.get("medoid_sample_id", row["sample_id"]))
        payload = {"cluster_id": cluster_id, "size": len(members), "medoid": next(row for row in members if row["sample_id"] == medoid_id), "members": members}
        system, user = cluster_audit_prompt(payload)
        result = client.generate(system_prompt=system, user_prompt=user, schema=cluster_audit_schema(),
                                 metadata={"stage": "cluster_audit", "cluster_id": cluster_id},
                                 validator=validate_cluster_audit)
        audits.append(result.output)
        member_audit_rows.extend({"cluster_id": cluster_id, "sample_id": row.get("sample_id"),
                                 "original_text": row.get("original_text"),
                                 "canonical_reasoning": row.get("canonical_reasoning")} for row in members)
        append_jsonl(output / "cluster_audits.jsonl", result.output)
    passed = bool(audits) and not any(row["member_consistency"] == "LOW" and row["medoid_representative"] == "NO" for row in audits)
    write_json(output / "cluster_gate.json", {"passed": passed, "cluster_count": len(audits), "audits": audits})
    with (output / "cluster_member_audit.jsonl").open("w", encoding="utf-8") as stream:
        for row in member_audit_rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    (output / "cluster_member_audit.md").write_text("# Cluster Member Audit\n\n" + "\n".join(f"- Cluster {row['cluster_id']}: {row['member_consistency']} / {row['medoid_representative']}" for row in audits) + "\n", encoding="utf-8")
    return {"passed": passed, "audits": audits}


def induce_cluster_modes(config, client=None):
    _gate(config)
    output = Path(config.output_dir)
    audits = read_jsonl(output / "cluster_audits.jsonl")
    member_rows = read_jsonl(output / "cluster_member_audit.jsonl") if (output / "cluster_member_audit.jsonl").exists() else []
    client = client or _client(config)
    modes = []
    existing = {row["cluster_id"]: row for row in read_jsonl(output / "cluster_modes.jsonl")} if (output / "cluster_modes.jsonl").exists() else {}
    for audit in audits:
        if audit["cluster_id"] in existing:
            modes.append(existing[audit["cluster_id"]])
            continue
        system, user = cluster_mode_prompt(audit, [row for row in member_rows if row["cluster_id"] == audit["cluster_id"]])
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
    merge_plan = json.loads((output / "mode_merge_plan.json").read_text(encoding="utf-8")) if (output / "mode_merge_plan.json").exists() else {"merge_groups": [], "keep_separate": []}
    provenance = json.loads((output / "run_manifest.json").read_text(encoding="utf-8")) if (output / "run_manifest.json").exists() else {"sample_count": len(read_jsonl(output / "semantic_records.jsonl"))}
    client = client or _client(config)
    system, user = final_definition_prompt(config.label, modes, merge_plan)
    result = client.generate(system_prompt=system, user_prompt=user, schema=final_definition_schema(),
                             metadata={"stage": "final_definition"}, validator=validate_final_definition)
    value = result.output
    lines = [f"# Induced Definition — {config.label}", "", "## 1. Core invariant", "", value["core_invariant"], "", "## 2. Prototypical inferential relation", "", value["prototypical_relation"], "", "## 3. Discovered reasoning modes", ""]
    for mode in value["discovered_modes"]:
        lines.extend([f"### {mode['mode_name']}", f"Clusters: {', '.join(map(str, mode['cluster_ids']))}", f"Coverage: {mode['coverage_n']}", f"Relation: {mode['relation']}", f"Representative member IDs: {', '.join(mode['supporting_member_ids'])}", ""])
    lines.extend(["## 4. Boundary conditions", "", "### Not sufficient", *[f"- {item}" for item in value["not_sufficient"]], "", "### Opposite-direction cases", *[f"- {item}" for item in value["opposite_direction_cases"]], "", "### Descriptive / non-inferential cases", *[f"- {item}" for item in value["descriptive_cases"]], "", "## 5. Dataset-edge / noisy modes", *[f"- {item}" for item in value["dataset_edge_modes"]], "", "## 6. Operational classification test", *[f"{index}. {item}" for index, item in enumerate(value["operational_classification_test"], 1)], "", "## 7. Provenance", *[f"{key}: {item}" for key, item in provenance.items()], "", f"Conclusion: {value['status']}", ""])
    text = "\n".join(lines)
    (output / "induced_definition.md").write_text(text, encoding="utf-8")
    return {"path": str(output / "induced_definition.md"), "status": "PARTIALLY READY"}

