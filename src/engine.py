import json
import time
from dataclasses import replace

from src.adjudication import adjudication_route, build_candidate_dossiers
from src.data.loader import ModelInput
from src.evidence import reference_schema, resolve_evidence, target_passages
from src.labels import ANALYSTS, labels_for
from src.prompts import system_prompt
from src.schemas import (
    comparative_adjudicator_schema,
    counterargument_schema,
    goal_schema,
    structure_schema,
    validate_comparative_adjudicator_semantics,
    validate_counterargument_semantics,
    validate_goal_semantics,
    validate_structure_semantics,
)
from src.trace import aggregate_call_stats


SCHEMAS = {
    "structure": structure_schema,
    "goal": goal_schema,
    "counterargument": counterargument_schema,
}


VALIDATORS = {
    "structure": validate_structure_semantics,
    "goal": validate_goal_semantics,
    "counterargument": validate_counterargument_semantics,
}


def _negative_hypothesis(reports):
    negative = []
    for role in ANALYSTS:
        report = reports[role]
        if report["verdict"] == "Non-Fallacious":
            negative.append({
                "source": role,
                "decision_reason": report["decision_reason"],
                "opposing_reason": report["opposing_reason"],
                "evidence_ids": report.get("evidence_ids", []),
                "evidence_spans": report.get("evidence_spans", []),
            })
    if negative:
        return negative
    return [
        {
            "source": role,
            "decision_reason": reports[role]["opposing_reason"],
            "opposing_reason": reports[role]["decision_reason"],
            "evidence_ids": reports[role].get("evidence_ids", []),
            "evidence_spans": reports[role].get("evidence_spans", []),
        }
        for role in ANALYSTS
    ]


class Engine:
    def __init__(self, llm, *, task):
        labels_for(task)
        self.llm = llm
        self.task = task

    def run(self, model_input: ModelInput, metadata, on_stage=None):
        if not isinstance(model_input, ModelInput):
            raise TypeError("Engine accepts only label-free ModelInput")

        started = time.monotonic()
        calls = []
        reports = {}
        on_stage = on_stage or (lambda stage, output: None)
        safe_metadata = {
            key: metadata[key]
            for key in ("sample_id", "split", "dataset", "experiment")
            if key in metadata
        }

        for role in ANALYSTS:
            result = self._call(
                role=role,
                stage=role,
                model_input=model_input,
                metadata=safe_metadata,
                schema=SCHEMAS[role](self.task),
                payload={"stage": role, "task": self.task},
                extra_validator=lambda output, r=role: VALIDATORS[r](output, self.task),
            )
            calls.append(result)
            reports[role] = result.output
            on_stage(role, result.output)

        dossiers = build_candidate_dossiers(self.task, reports)
        route = adjudication_route(self.task, dossiers)
        candidates = route["allowed_candidates"]

        if route["action"] == "direct":
            selected = route["selected_candidate"]
            source = dossiers[0]["support"][0]
            adjudication = {
                "selected_verdict": "Fallacious",
                "selected_candidate": selected,
                "evidence_ids": source["evidence_ids"],
                "evidence_spans": source["evidence_spans"],
                "decisive_condition": source["mandatory_condition"],
                "decision_reason": source["decision_reason"],
                "rejected_candidates": [],
                "status": "direct_unanimous_singleton",
            }
            on_stage("direct_decision", adjudication)
        else:
            payload = {
                "stage": "comparative_adjudication",
                "task": self.task,
                "recovery_mode": route["recovery"],
                "allowed_candidates": candidates,
                "initial_analysis": reports,
                "candidate_dossiers": dossiers,
            }
            if self.task == "detection":
                payload["non_fallacious_hypothesis"] = _negative_hypothesis(reports)

            result = self._call(
                role="comparative_arbiter",
                stage="comparative_adjudication",
                model_input=model_input,
                metadata=safe_metadata,
                schema=comparative_adjudicator_schema(self.task, candidates),
                payload=payload,
                extra_validator=lambda output: validate_comparative_adjudicator_semantics(
                    output,
                    self.task,
                    candidates,
                ),
            )
            calls.append(result)
            adjudication = {**result.output, "status": "comparative_adjudication"}
            selected = result.output["selected_candidate"]
            on_stage("comparative_adjudication", result.output)

        prediction = (
            adjudication["selected_verdict"]
            if self.task == "detection"
            else selected
        )
        initial_state = [
            {
                "source": role,
                "candidate": reports[role]["candidate"],
                "viable": reports[role]["condition_satisfied"],
                "reason": reports[role]["decision_reason"],
            }
            for role in ANALYSTS
        ]
        proposed = [item["candidate"] for item in dossiers]
        recovery = {
            "triggered": route["recovery"],
            "reason": "no_proposed_candidate" if route["recovery"] else None,
            "mode": "full_label_space" if route["recovery"] else None,
            "candidates": candidates if route["recovery"] else [],
        }
        candidate_state = {
            "initial": initial_state,
            "after_viability": proposed,
            "transitions": [],
            "after_conflicts": proposed,
            "recovery": recovery,
            "final_survivors": proposed,
            "dossiers": dossiers,
            "route": route,
        }
        return {
            "prediction": prediction,
            "selected_candidate": selected,
            "initial_analysis": reports,
            "conflicts": [],
            "candidate_state": candidate_state,
            "arbiter": {
                **adjudication,
                "verified": selected is not None,
                "rejection_reason": (
                    adjudication["decision_reason"] if selected is None else None
                ),
            },
            "stats": aggregate_call_stats(calls, time.monotonic() - started),
        }

    def _call(
        self,
        *,
        role,
        stage,
        model_input,
        metadata,
        schema,
        payload,
        extra_validator=None,
    ):
        passages = target_passages(model_input.comment)
        wire_schema = reference_schema(schema, passages)
        user_payload = {
            **payload,
            "input": {
                "title": model_input.title,
                "parent": model_input.parent_comment,
                "target": model_input.comment,
                "target_passages": passages,
                **({"article": model_input.article} if model_input.article is not None else {}),
            },
        }

        result = self.llm.generate(
            system_prompt=system_prompt(role),
            user_prompt=json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
            schema=wire_schema,
            metadata={
                **metadata,
                "task": self.task,
                "role": role,
                "stage": stage,
            },
            validator=extra_validator,
        )
        return replace(result, output=resolve_evidence(result.output, passages))
