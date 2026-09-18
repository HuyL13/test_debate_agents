import json
import time
from dataclasses import replace
from src.evidence import target_passages, reference_schema, resolve_evidence

from src.conflicts import choose_next_conflict, slug
from src.data.loader import ModelInput
from src.labels import ANALYSTS, labels_for
from src.prompts import system_prompt
from src.schemas import (
    derive_candidate,
    arbiter_schema,
    counterargument_schema,
    conflict_resolution_schema,
    goal_schema,
    structure_schema,
    validate_arbiter_semantics,
    validate_counterargument_semantics,
    validate_conflict_resolution_semantics,
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


def _unique(values):
    result = []
    for value in values:
        if value is not None and value not in result:
            result.append(value)
    return result


def _candidate_state(reports):
    entries = []

    for role in ANALYSTS:
        report = reports[role]
        candidate = report.get("candidate")

        if role == "structure":
            viable = (
                candidate is not None
                and report.get("structure_complete") is True
            )
            reason = (
                "structure_complete=true"
                if viable
                else "structure_complete=false"
            )

        elif role == "goal":
            viable = (
                candidate is not None
                and report.get("mechanism_supports_goal") is True
            )
            reason = (
                "mechanism_supports_goal=true"
                if viable
                else "mechanism_supports_goal=false"
            )

        else:
            viable = (
                candidate is not None
                and report.get("failure_exposed") is True
            )
            reason = (
                "failure_exposed=true"
                if viable
                else "failure_exposed=false"
            )

        entries.append({
            "source": role,
            "candidate": candidate,
            "viable": viable,
            "reason": reason,
        })

    active = _unique(
        entry["candidate"]
        for entry in entries
        if entry["viable"]
    )

    return entries, active


def _proposed_candidates(reports):
    return _unique(
        reports[role].get("candidate")
        for role in ANALYSTS
    )


def _survivor_support(reports, candidate_state, survivors, *, viable_only=True):
    survivors = set(survivors)
    support = {candidate: [] for candidate in survivors}
    state_by_source = {
        entry["source"]: entry
        for entry in candidate_state
    }

    for role in ANALYSTS:
        report = reports[role]
        state = state_by_source[role]
        candidate = report.get("candidate")

        if (viable_only and not state["viable"]) or candidate not in survivors:
            continue

        item = {
            "source": role,
            "evidence_ids": report.get("evidence_ids", []),
            "evidence_spans": report.get("evidence_spans", []),
        }

        if role == "structure":
            item["structure_type"] = report["structure_type"]
            item["slots"] = report["slots"]
            item["structure_complete"] = report["structure_complete"]

        elif role == "goal":
            item["conclusion_or_goal"] = report["conclusion_or_goal"]
            item["supporting_reason"] = report["supporting_reason"]
            item["support_relation"] = report["support_relation"]
            item["label_justification"] = report["label_justification"]
            item["mechanism_supports_goal"] = report["mechanism_supports_goal"]

        else:
            item["decisive_counterargument"] = report["decisive_counterargument"]
            item["challenged_inference"] = report["challenged_inference"]
            item["label_justification"] = report["label_justification"]
            item["failure_exposed"] = report["failure_exposed"]

        support[candidate].append(item)

    return support


class Engine:
    def __init__(self, llm, *, task):
        labels_for(task)
        self.llm = llm
        self.task = task

    def run(self, model_input: ModelInput, metadata):
        if not isinstance(model_input, ModelInput):
            raise TypeError("Engine accepts only label-free ModelInput")

        started = time.monotonic()
        calls = []
        reports = {}

        safe_metadata = {
            k: metadata[k]
            for k in ("sample_id", "split", "dataset", "experiment")
            if k in metadata
        }

        # ----------------------------------------------------
        # Initial independent analysts
        # ----------------------------------------------------

        for role in ANALYSTS:
            result = self._call(
                role=role,
                stage=role,
                model_input=model_input,
                metadata=safe_metadata,
                schema=SCHEMAS[role](self.task),
                payload={
                    "stage": role,
                    "task": self.task,
                },
                extra_validator=VALIDATORS[role],
            )

            calls.append(result)
            reports[role] = {**result.output, "candidate": derive_candidate(role, result.output)}

        initial_state, active_candidates = _candidate_state(reports)

        # ----------------------------------------------------
        # Dynamic conflict resolution over viable candidates
        # ----------------------------------------------------

        survivors = list(active_candidates)
        resolutions = []
        transitions = []

        while len(survivors) > 1 and len(resolutions) < 2:
            conflict = choose_next_conflict(survivors)
            if conflict is None:
                break

            pair = conflict["candidates"]
            support = _survivor_support(
                reports,
                initial_state,
                pair,
            )

            stage = (
                "resolve__"
                + "__vs__".join(slug(candidate) for candidate in pair)
            )

            result = self._call(
                role="resolver",
                stage=stage,
                model_input=model_input,
                metadata=safe_metadata,
                schema=conflict_resolution_schema(
                    self.task,
                    pair,
                ),
                payload={
                    "stage": stage,
                    "task": self.task,
                    "conflict": conflict,
                    "survivor_support": support,
                    "allowed_winners": pair,
                },
                extra_validator=lambda output, p=pair: (
                    validate_conflict_resolution_semantics(output, p)
                ),
            )

            calls.append(result)

            before = list(survivors)
            winner = result.output["winner"]

            survivors = [
                candidate
                for candidate in survivors
                if candidate not in pair
            ]

            if winner is not None and winner not in survivors:
                survivors.append(winner)

            resolution = {
                **conflict,
                "resolution": result.output,
            }
            resolutions.append(resolution)

            transitions.append({
                "before": before,
                "conflict": conflict["id"],
                "winner": winner,
                "after": list(survivors),
            })

        # ----------------------------------------------------
        # Final adjudication
        # ----------------------------------------------------

        post_conflict_survivors = list(survivors)
        recovery = {
            "triggered": False,
            "reason": None,
            "mode": None,
            "candidates": [],
        }

        if self.task == "detection" and not survivors:
            adjudication = {
                "selected_candidate": None,
                "verified": False,
                "evidence_spans": [],
                "decisive_condition": "none",
                "rejection_reason": (
                    "No candidate survived role-specific viability checks."
                ),
                "status": "skipped_no_survivor",
            }
            selected_candidate = None

        else:
            arbiter_role = "arbiter"
            arbiter_stage = "arbiter"
            support_viable_only = True
            arbiter_payload = {
                "stage": arbiter_stage,
                "task": self.task,
            }

            if self.task == "classification" and not survivors:
                proposed = _proposed_candidates(reports)
                if proposed:
                    survivors = list(proposed)
                    recovery_mode = "proposed_candidates"
                else:
                    survivors = list(labels_for("classification"))
                    recovery_mode = "full_label_space"

                recovery = {
                    "triggered": True,
                    "reason": "no_viable_survivor",
                    "mode": recovery_mode,
                    "candidates": list(survivors),
                }
                arbiter_role = "recovery_arbiter"
                arbiter_stage = "classification_recovery"
                support_viable_only = False
                arbiter_payload = {
                    "stage": arbiter_stage,
                    "task": self.task,
                    "recovery_mode": recovery_mode,
                    "allowed_candidates": list(survivors),
                    "initial_analysis": reports,
                }

            support = _survivor_support(
                reports,
                initial_state,
                survivors,
                viable_only=support_viable_only,
            )

            if recovery["triggered"]:
                arbiter_payload["candidate_support"] = support
            else:
                # Normal adjudication sees only hypotheses that survived the
                # task-specific viability checks and conflict resolution.
                arbiter_payload["surviving_candidates"] = list(survivors)
                arbiter_payload["survivor_support"] = support

            arbiter = self._call(
                role=arbiter_role,
                stage=arbiter_stage,
                model_input=model_input,
                metadata=safe_metadata,
                schema=arbiter_schema(
                    self.task,
                    survivors,
                ),
                payload=arbiter_payload,
                extra_validator=lambda output, s=list(survivors), t=self.task: (
                    validate_arbiter_semantics(
                        output,
                        s,
                        require_selection=(t == "classification"),
                    )
                ),
            )

            calls.append(arbiter)
            selected_candidate = arbiter.output["selected_candidate"]
            adjudication = {
                **arbiter.output,
                "verified": selected_candidate is not None,
                "rejection_reason": (
                    arbiter.output["decision_reason"] if selected_candidate is None else None
                ),
                "status": (
                    "classification_recovery"
                    if recovery["triggered"]
                    else "adjudicated"
                ),
            }

        # ----------------------------------------------------
        # Deterministic benchmark mapping
        # ----------------------------------------------------

        if self.task == "detection":
            prediction = (
                "Fallacious"
                if selected_candidate is not None
                else "Non-Fallacious"
            )
        else:
            # Classification is a forced-choice task. The schema and semantic
            # validator above guarantee that this is one of the eight labels.
            prediction = selected_candidate

        stats = aggregate_call_stats(
            calls,
            time.monotonic() - started,
        )

        candidate_state = {
            "initial": initial_state,
            "after_viability": active_candidates,
            "transitions": transitions,
            "after_conflicts": post_conflict_survivors,
            "recovery": recovery,
            "final_survivors": survivors,
        }

        return {
            "prediction": prediction,
            "selected_candidate": selected_candidate,
            "initial_analysis": reports,
            "conflicts": resolutions,
            "candidate_state": candidate_state,
            "arbiter": adjudication,
            "stats": stats,
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
        schema = reference_schema(schema, passages)
        user_payload = {
            **payload,
            "input": {
                "title": model_input.title,
                "parent": model_input.parent_comment,
                "target": model_input.comment,
                "target_passages": passages,
                **(
                    {"article": model_input.article}
                    if model_input.article is not None
                    else {}
                ),
            },
        }

        def validator(output):
            if extra_validator is not None:
                extra_validator(output)

        result = self.llm.generate(
            system_prompt=system_prompt(role),
            user_prompt=json.dumps(
                user_payload,
                ensure_ascii=False,
                sort_keys=True,
            ),
            schema=schema,
            metadata={
                **metadata,
                "task": self.task,
                "role": role,
                "stage": stage,
            },
            validator=validator,
        )
        return replace(result, output=resolve_evidence(result.output, passages))
