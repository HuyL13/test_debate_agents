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
        conflicts = build_conflicts(reports)
        resolutions = []
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
            },
        )
        calls.append(arbiter)
        stats = aggregate_call_stats(calls, time.monotonic() - started)
        return {
            "prediction": arbiter.output["prediction"],
            "initial_analysis": reports,
            "conflicts": resolutions,
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
