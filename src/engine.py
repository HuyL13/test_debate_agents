import json
import time

from src.conflicts import build_conflicts, slug
from src.data.loader import ModelInput
from src.labels import ANALYSTS, labels_for
from src.prompts import system_prompt
from src.schemas import (
    arbiter_schema,
    conflict_resolution_schema,
    critical_schema,
    enthymeme_schema,
    scheme_schema,
    validate_evidence_spans,
)
from src.trace import aggregate_call_stats


SCHEMAS = {
    "scheme": scheme_schema,
    "enthymeme": enthymeme_schema,
    "critical": critical_schema,
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
        if role == "scheme":
            viable = candidate is not None and report.get("structure_complete") is True
            reason = "structure_complete=true" if viable else "structure_complete=false"
        elif role == "enthymeme":
            viable = candidate is not None and report.get("assumption_licensed") is True
            reason = "assumption_licensed=true" if viable else "assumption_licensed=false"
        else:
            viable = candidate is not None and report.get("criterion_met") is True
            reason = "criterion_met=true" if viable else "criterion_met=false"
        entries.append({"source": role, "candidate": candidate, "viable": viable, "reason": reason})
    active = _unique(entry["candidate"] for entry in entries if entry["viable"])
    return entries, active


def _reports_for_active_candidates(active):
    roles = ("scheme", "enthymeme", "critical")
    reports = {}
    for index, role in enumerate(roles):
        reports[role] = {"candidate": active[index] if index < len(active) else None}
    return reports


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
        safe_metadata = {k: metadata[k] for k in ("sample_id", "split", "dataset", "experiment") if k in metadata}
        for role in ANALYSTS:
            result = self._call(
                role=role,
                stage=role,
                model_input=model_input,
                metadata=safe_metadata,
                schema=SCHEMAS[role](self.task),
                payload={"stage": role, "task": self.task},
            )
            calls.append(result)
            reports[role] = result.output
        initial_state, active_candidates = _candidate_state(reports)
        conflicts = build_conflicts(_reports_for_active_candidates(active_candidates)) if len(active_candidates) > 1 else []
        resolutions = []
        survivors = list(active_candidates)
        for conflict in conflicts[:2]:
            stage = "resolve__" + "__vs__".join(slug(candidate) for candidate in conflict["candidates"])
            result = self._call(
                role="resolver",
                stage=stage,
                model_input=model_input,
                metadata=safe_metadata,
                schema=conflict_resolution_schema(self.task, conflict["candidates"]),
                payload={
                    "stage": stage,
                    "task": self.task,
                    "conflict": conflict,
                    "reports": reports,
                    "allowed_winners": conflict["candidates"],
                },
            )
            calls.append(result)
            resolutions.append({**conflict, "resolution": result.output})
            winner = result.output.get("winner")
            pair = set(conflict["candidates"])
            survivors = [candidate for candidate in survivors if candidate not in pair]
            if winner is not None and winner not in survivors:
                survivors.append(winner)
        arbiter = self._call(
            role="arbiter",
            stage="arbiter",
            model_input=model_input,
            metadata=safe_metadata,
            schema=arbiter_schema(self.task),
            payload={
                "stage": "arbiter",
                "task": self.task,
                "reports": reports,
                "resolutions": resolutions,
                "surviving_candidates": survivors,
            },
        )
        calls.append(arbiter)
        stats = aggregate_call_stats(calls, time.monotonic() - started)
        return {
            "prediction": arbiter.output["prediction"],
            "initial_analysis": reports,
            "conflicts": resolutions,
            "candidate_state": {
                "initial": initial_state,
                "after_viability": active_candidates,
                "after_conflicts": survivors,
            },
            "arbiter": arbiter.output,
            "stats": stats,
        }

    def _call(self, *, role, stage, model_input, metadata, schema, payload):
        user_payload = {
            **payload,
            "input": {
                "title": model_input.title,
                "parent": model_input.parent_comment,
                "target": model_input.comment,
                **({"article": model_input.article} if model_input.article is not None else {}),
            },
        }
        return self.llm.generate(
            system_prompt=system_prompt(role),
            user_prompt=json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
            schema=schema,
            metadata={**metadata, "task": self.task, "role": role, "stage": stage},
            validator=lambda output: validate_evidence_spans(output, model_input.comment),
        )
