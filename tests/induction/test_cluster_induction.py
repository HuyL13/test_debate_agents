import json

import pytest

from src.induction.config import load_config_from_mapping
from src.induction.contracts import validate_cluster_audit
from src.induction.induction import induce_cluster_modes, render_induced_definition


def valid_cluster_audit():
    return {
        "cluster_id": 0,
        "main_reasoning_relation": "a premise supports a conclusion",
        "shared_invariant": "the same bridge is used",
        "variation_within_cluster": "topics vary",
        "member_consistency": "HIGH",
        "medoid_representative": "YES",
        "secondary_patterns": [],
        "outlier_ids": [],
        "possible_semantic_extraction_errors": [],
        "possible_mislabel_or_intrinsic_overlap": [],
    }


def mode_with_ids(cluster_id, member_ids):
    return {
        "cluster_id": cluster_id,
        "mode_name": "A discovered mode",
        "premise_pattern": "A premise",
        "conclusion_pattern": "A conclusion",
        "core_bridge": "A bridge",
        "canonical_template": "PREMISE -> BRIDGE -> CONCLUSION",
        "non_invariant_details": [],
        "boundary_notes": [],
        "supporting_member_ids": member_ids,
        "coverage_n": len(member_ids),
    }


def config_for_output(tmp_path):
    return load_config_from_mapping({"base_dir": str(tmp_path), "data": {"path": "train.json", "label": "Appeal to Tradition"}, "output_dir": "output"})


def test_cluster_audit_schema_requires_consistency_and_representativeness():
    value = valid_cluster_audit()
    del value["member_consistency"]
    with pytest.raises(ValueError, match="member_consistency"):
        validate_cluster_audit(value)


def test_mode_induction_stops_when_cluster_gate_fails(tmp_path):
    config = config_for_output(tmp_path)
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "cluster_gate.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="cluster audit"):
        induce_cluster_modes(config)


def test_final_definition_contains_supporting_cluster_and_sample_ids():
    result = render_induced_definition(
        label="Appeal to Tradition",
        modes=[mode_with_ids(3, ["1:c1"])],
        provenance={"selected_k": 7},
    )
    assert "Cluster 3" in result
    assert "1:c1" in result
    assert "selected_k" in result
