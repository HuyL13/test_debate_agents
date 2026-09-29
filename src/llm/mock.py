"""Deterministic transport for plumbing smoke tests. NOT an LLM or benchmark."""
import json

from src.io_utils import digest


def _target(payload):
    user = json.loads(payload["messages"][1]["content"])
    return user.get("input", {}).get("target", json.dumps(user, ensure_ascii=False))


def _user(payload):
    return json.loads(payload["messages"][1]["content"])


def _span(text):
    return text[:120] if text else "empty"


class MockTransport:
    def complete(self, payload):
        properties = payload["response_format"]["json_schema"]["schema"]["properties"]
        stage = json.loads(payload["messages"][1]["content"]).get("stage", "")
        target = _target(payload)
        span = "good and evil" if "good and evil" in target else _span(target)
        negative = "good and evil" in target
        if stage == "semantic_extraction":
            value = {
                "article_id": _user(payload)["article_id"],
                "comment_id": _user(payload)["sample_id"].split(":", 1)[1],
                "original_text": target,
                "premises": ["A claim is asserted in the target comment."],
                "conclusion": "The target claim should be accepted or rejected.",
                "inference_source": "stated premise",
                "inference_target": "stated conclusion",
                "bridge": "The premise is treated as support for the conclusion.",
                "evidential_basis": "the target argument",
                "premise_valence": "NEUTRAL",
                "relation_polarity": "OTHER",
                "conclusion_direction": "accept or reject",
                "missing_justification": None,
                "alternatives_suppressed": None,
                "causal_chain": None,
                "canonical_reasoning": "A stated premise is treated as support for a related conclusion.",
                "ambiguity_notes": None,
                "topic_leakage_check": False,
            }
        elif "member_consistency" in properties:
            cluster = _user(payload).get("cluster", {}).get("cluster_id", 0)
            value = {
                "cluster_id": cluster,
                "main_reasoning_relation": "The cluster shares an inferential relation.",
                "shared_invariant": "A premise supports a conclusion through a bridge.",
                "variation_within_cluster": "Topics vary across members.",
                "member_consistency": "HIGH",
                "medoid_representative": "YES",
                "secondary_patterns": [], "outlier_ids": [],
                "possible_semantic_extraction_errors": [],
                "possible_mislabel_or_intrinsic_overlap": [],
            }
        elif "mode_name" in properties:
            audit = _user(payload).get("cluster_audit", {})
            cluster = audit.get("cluster_id", 0)
            value = {
                "cluster_id": cluster, "mode_name": "A discovered reasoning mode",
                "premise_pattern": "A premise is presented.",
                "conclusion_pattern": "A conclusion is drawn.",
                "core_bridge": "The premise is treated as support for the conclusion.",
                "canonical_template": "PREMISE -> BRIDGE -> CONCLUSION",
                "non_invariant_details": [], "boundary_notes": [],
                "supporting_member_ids": audit.get("outlier_ids", []) or ["unknown"],
                "coverage_n": 1,
            }
        elif "merge_groups" in properties:
            value = {"merge_groups": [], "keep_separate": []}
        elif stage == "property_graph_extraction":
            sample_id = _user(payload)["sample_id"]
            value = {
                "sample_id": sample_id,
                "propositions": [
                    {"id": "p1", "text": span, "speaker": "target", "role": "premise"},
                    {"id": "p2", "text": span, "speaker": "target", "role": "conclusion"},
                ],
                "relations": [{
                    "source": "p1", "target": "p2", "type": "USED_AS_JUSTIFICATION",
                    "status": "asserted", "explicitness": "implicit", "evidence_spans": [span],
                }],
                "semantic_roles": {
                    "source_type": "unspecified", "sample_scope": "unspecified",
                    "target_scope": "unspecified", "alternatives_count": None,
                    "property_type": "unspecified", "comparison_target": None,
                },
                "qualifiers": {"certainty": "unspecified", "universality": "unspecified", "normative": False},
                "structural_features": ["premise_to_conclusion", "implicit_justification"],
                "uncertainties": [],
            }
        elif "structure_complete" in properties:
            value = {
                "evidence_spans": [span],
                "verdict": "Non-Fallacious" if negative else "Fallacious",
                "candidate": None if negative else "Slippery Slope",
                "mandatory_condition": None if negative else "An unsupported consequence progression is asserted.",
                "condition_satisfied": not negative,
                "decision_reason": "No listed structure is present." if negative else "The target asserts escalation.",
                "opposing_reason": "A hidden contrast defect might exist." if negative else "The warning may be proportionate.",
                "structure_type": "none" if negative else "consequence_chain",
                "slots": [] if negative else [
                    {"role": "initial_event", "text": span},
                    {"role": "intermediate_consequence", "text": span},
                    {"role": "final_consequence", "text": span},
                ],
                "structure_complete": not negative,
                "premise": None if negative else span,
                "conclusion": None if negative else span,
                "inferential_link": None if negative else "The initial event is claimed to escalate.",
            }
        elif "mechanism_supports_goal" in properties:
            if negative:
                value = {
                    "evidence_spans": [span],
                    "verdict": "Non-Fallacious",
                    "mandatory_condition": None,
                    "condition_satisfied": False,
                    "decision_reason": "The moral contrast does not instantiate a listed fallacy.",
                    "opposing_reason": "The contrast might oversimplify the issue.",
                    "conclusion_or_goal": "make a moral contrast",
                    "candidate": None,
                    "supporting_reason": None,
                    "support_relation": None,
                    "label_justification": "Moral contrast alone is not a fallacy.",
                    "mechanism_supports_goal": False,
                    "fallacy_owned_by_target": True,
                }
            else:
                value = {
                    "evidence_spans": [span],
                    "verdict": "Fallacious",
                    "mandatory_condition": "An unsupported consequence progression is asserted.",
                    "condition_satisfied": True,
                    "decision_reason": "The escalation does justificatory work.",
                    "opposing_reason": "The warning may be proportionate.",
                    "conclusion_or_goal": "warn against the initial action",
                    "candidate": "Slippery Slope",
                    "supporting_reason": "Rights will be lost after allowing the action.",
                    "support_relation": "Predicted escalation is used to oppose the action.",
                    "label_justification": "The warning assumes unestablished escalation.",
                    "mechanism_supports_goal": True,
                    "fallacy_owned_by_target": True,
                }
        elif "failure_exposed" in properties:
            value = {
                "evidence_spans": [span],
                "verdict": "Non-Fallacious" if negative else "Fallacious",
                "mandatory_condition": None if negative else "An unsupported consequence progression is asserted.",
                "condition_satisfied": not negative,
                "decision_reason": "The defense defeats the objection." if negative else "The objection defeats the defense.",
                "opposing_reason": "The contrast may oversimplify." if negative else "The warning may be proportionate.",
                "decisive_counterargument": None if negative else (
                    "The escalation is asserted but not established by the stated reasoning."
                ),
                "candidate": None if negative else "Slippery Slope",
                "challenged_inference": None if negative else "The initial action leads to escalation.",
                "label_justification": "No reasoning defect in the contrast." if negative else "Unestablished escalation supports Slippery Slope.",
                "failure_exposed": not negative,
                "strongest_objection": "The reasoning may oversimplify or escalate.",
                "strongest_defense": "The target states a permissible contrast or warning.",
                "winning_side": "defense" if negative else "objection",
            }
        elif "winner" in properties:
            allowed = properties["winner"].get("enum") or properties["winner"]["anyOf"][0].get("enum", [])
            winner = None if any(item.get("type") == "null" for item in properties["winner"].get("anyOf", [])) else allowed[0]
            value = {
                "winner": winner,
                "evidence_spans": [span],
                "decisive_test": "offline targeted discriminator",
                "loser_failure": "offline losing mandatory condition failed",
            }
        elif "selected_candidate" in properties:
            selected_schema = properties["selected_candidate"]
            allowed = []

            if "enum" in selected_schema:
                allowed = selected_schema["enum"]
            else:
                for option in selected_schema.get("anyOf", []):
                    allowed.extend(option.get("enum", []))

            task = _user(payload).get("task")
            if allowed and not (task == "detection" and negative):
                selected = allowed[0]
                value = {
                    "selected_verdict": "Fallacious",
                    "selected_candidate": selected,
                    "evidence_spans": [span],
                    "decisive_condition": (
                        "consequence_chain"
                        if selected == "Slippery Slope"
                        else "target_fallacy_condition"
                    ),
                    "decision_reason": "The target supports the stated escalation hypothesis.",
                    "rejected_candidates": [],
                }
            else:
                value = {
                    "selected_verdict": "Non-Fallacious",
                    "selected_candidate": None,
                    "evidence_spans": [span],
                    "decisive_condition": "none",
                    "decision_reason": "No surviving hypothesis is supported.",
                    "rejected_candidates": [],
                }
        else:
            raise ValueError(f"Unknown mock schema for stage: {stage}")
        if "evidence_ids" in properties:
            value.pop("evidence_spans", None)
            value["evidence_ids"] = properties["evidence_ids"]["items"]["enum"][:1]
        return {
            "id": "mock-" + digest({"stage": stage, "target": target})[:12],
            "model": "offline-mock-v1",
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value), "refusal": None}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
