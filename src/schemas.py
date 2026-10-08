import re

from src.labels import FALLACIES, labels_for


STRUCTURE_TYPES = (
    "authority_to_claim",
    "popularity_to_claim",
    "nature_to_value",
    "tradition_to_preservation",
    "worse_problem_to_deprioritization",
    "exhaustive_alternatives",
    "sample_to_population",
    "consequence_chain",
    "none",
)

SLOT_ROLES = (
    "authority",
    "endorsed_claim",
    "population_group",
    "popularity_claim",
    "target_claim",
    "naturalness_premise",
    "evaluative_conclusion",
    "tradition_premise",
    "preservation_conclusion",
    "focal_issue",
    "worse_issue",
    "deprioritizing_conclusion",
    "alternative_a",
    "alternative_b",
    "exhaustiveness_commitment",
    "sample",
    "observed_property",
    "target_population",
    "initial_event",
    "intermediate_consequence",
    "final_consequence",
)

SUPPORT_MECHANISMS = (
    "authority_support",
    "popularity_support",
    "naturalness_support",
    "tradition_support",
    "worse_problem_downplay",
    "exhaustive_choice_pressure",
    "sample_to_general_claim",
    "escalating_consequence_warning",
    "other",
    "none",
)

FAILURE_MODES = (
    "authority_not_sufficient",
    "popularity_not_evidence",
    "naturalness_not_normative",
    "tradition_not_justification",
    "worse_problem_irrelevant",
    "alternatives_not_exhaustive",
    "sample_not_representative",
    "escalation_not_established",
    "other",
    "none",
)

DECISIVE_CONDITIONS = STRUCTURE_TYPES + SUPPORT_MECHANISMS + FAILURE_MODES

STRUCTURE_BY_CANDIDATE = {
    "Appeal to Authority": "authority_to_claim",
    "Appeal to Majority": "popularity_to_claim",
    "Appeal to Nature": "nature_to_value",
    "Appeal to Tradition": "tradition_to_preservation",
    "Appeal to Worse Problems": "worse_problem_to_deprioritization",
    "False Dilemma": "exhaustive_alternatives",
    "Hasty Generalization": "sample_to_population",
    "Slippery Slope": "consequence_chain",
}

REQUIRED_SLOTS = {
    "Appeal to Authority": {"authority", "endorsed_claim"},
    "Appeal to Majority": {"population_group", "popularity_claim", "target_claim"},
    "Appeal to Nature": {"naturalness_premise", "evaluative_conclusion"},
    "Appeal to Tradition": {"tradition_premise", "preservation_conclusion"},
    "Appeal to Worse Problems": {"focal_issue", "worse_issue", "deprioritizing_conclusion"},
    "False Dilemma": {"alternative_a", "alternative_b", "exhaustiveness_commitment"},
    "Hasty Generalization": {"sample", "observed_property", "target_population"},
    "Slippery Slope": {"initial_event", "intermediate_consequence", "final_consequence"},
}



def object_schema(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": False,
    }


def _string(max_length=1200):
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def _spans():
    return {"type": "array", "items": _string(240), "minItems": 1, "maxItems": 3}


def _candidate(task):
    labels_for(task)
    return {"anyOf": [{"enum": list(FALLACIES)}, {"type": "null"}]}


def _nullable_string(max_length=1200):
    return {"anyOf": [_string(max_length), {"type": "null"}]}


def _analyst_fields(task):
    return {
        "verdict": {"enum": ["Fallacious", "Non-Fallacious"]},
        "candidate": _candidate(task),
        "mandatory_condition": _nullable_string(),
        "condition_satisfied": {"type": "boolean"},
        "decision_reason": _string(),
        "opposing_reason": _string(),
    }


def _slots():
    return {
        "type": "array",
        "items": object_schema({
            "role": {"enum": list(SLOT_ROLES)},
            "text": _string(240),
        }),
        "minItems": 0,
        "maxItems": 5,
    }


def structure_schema(task):
    labels_for(task)
    return object_schema({
        "evidence_spans": _spans(),
        **_analyst_fields(task),
        "structure_type": {"enum": list(STRUCTURE_TYPES)},
        "slots": _slots(),
        "structure_complete": {"type": "boolean"},
        "premise": _nullable_string(),
        "conclusion": _nullable_string(),
        "inferential_link": _nullable_string(),
    })


def goal_schema(task):
    labels_for(task)
    return object_schema({
        "evidence_spans": _spans(),
        **_analyst_fields(task),
        "conclusion_or_goal": {"anyOf": [_string(), {"type": "null"}]},
        "supporting_reason": {"anyOf": [_string(), {"type": "null"}]},
        "support_relation": {"anyOf": [_string(), {"type": "null"}]},
        "label_justification": _string(),
        "mechanism_supports_goal": {"type": "boolean"},
        "fallacy_owned_by_target": {"type": "boolean"},
    })


def counterargument_schema(task):
    labels_for(task)
    return object_schema({
        "evidence_spans": _spans(),
        **_analyst_fields(task),
        "decisive_counterargument": {"anyOf": [_string(), {"type": "null"}]},
        "challenged_inference": {"anyOf": [_string(), {"type": "null"}]},
        "label_justification": _string(),
        "failure_exposed": {"type": "boolean"},
        "strongest_objection": _string(),
        "strongest_defense": _string(),
        "winning_side": {"enum": ["objection", "defense", "unresolved"]},
    })


def comparative_adjudicator_schema(task, allowed_candidates):
    labels_for(task)
    allowed = list(dict.fromkeys(
        candidate for candidate in allowed_candidates if candidate is not None
    ))
    if task == "classification":
        selected = {"enum": allowed}
        verdict = {"enum": ["Fallacious"]}
    else:
        selected = (
            {"anyOf": [{"enum": allowed}, {"type": "null"}]}
            if allowed else {"type": "null"}
        )
        verdict = {"enum": ["Fallacious", "Non-Fallacious"]}
    rejected_item = object_schema({
        "candidate": {"enum": allowed},
        "failed_condition": _string(),
    })
    return object_schema({
        "selected_verdict": verdict,
        "selected_candidate": selected,
        "evidence_spans": _spans(),
        "decisive_condition": _string(),
        "decision_reason": _string(),
        "rejected_candidates": {
            "type": "array",
            "items": rejected_item,
            "minItems": 0,
            "maxItems": len(allowed),
        },
    })


def conflict_resolution_schema(task, allowed_candidates):
    labels_for(task)
    labels = [c for c in allowed_candidates if c is not None]
    winner = {"enum": labels}
    if None in allowed_candidates:
        winner = {"anyOf": [winner, {"type": "null"}]}
    return object_schema({
        "winner": winner,
        "evidence_spans": _spans(),
        "decisive_test": _string(),
        "loser_failure": _string(),
    })


def arbiter_schema(task, allowed_candidates):
    labels_for(task)
    allowed = [candidate for candidate in allowed_candidates if candidate is not None]

    if allowed:
        # Detection may reject all surviving hypotheses and map that to
        # Non-Fallacious. Classification is a forced-choice task over the
        # eight CoCoLoFa labels, so null is not a valid final decision.
        if task == "classification":
            selected = {"enum": allowed}
        else:
            selected = {
                "anyOf": [
                    {"enum": allowed},
                    {"type": "null"},
                ]
            }
    else:
        selected = {"type": "null"}

    return object_schema({
        "selected_candidate": selected,
        "evidence_spans": _spans(),
        "decisive_condition": _string(),
        "decision_reason": _string(),
    })


def derive_candidate(role, value):
    if role != "structure":
        return value["candidate"]
    return next((label for label, kind in STRUCTURE_BY_CANDIDATE.items()
                 if kind == value["structure_type"]), None)


def _validate_analyst_semantics(value, task):
    labels_for(task)
    candidate = value["candidate"]
    verdict = value["verdict"]
    if verdict == "Non-Fallacious" and candidate is not None:
        raise ValueError("A negative verdict cannot select a fallacy candidate")
    if verdict == "Fallacious" and candidate is None:
        raise ValueError("A positive verdict requires a fallacy candidate")
    if candidate is not None:
        _require_text(value, ("mandatory_condition",))
        if not value["condition_satisfied"]:
            raise ValueError("A positive candidate requires its mandatory condition")
    elif value["condition_satisfied"]:
        raise ValueError("A negative report cannot satisfy a fallacy condition")
    _require_text(value, ("decision_reason", "opposing_reason"))


def validate_structure_semantics(value, task="detection"):
    _validate_analyst_semantics(value, task)
    candidate = derive_candidate("structure", value)
    structure_type = value["structure_type"]
    complete = value["structure_complete"]

    if value["candidate"] != candidate:
        raise ValueError("Structure candidate must match structure_type")

    if candidate is None:
        if complete is not False or value["slots"]:
            raise ValueError("structure_type=none requires slots=[] and structure_complete=false")
        return value

    if complete:
        present = {slot["role"] for slot in value["slots"]}
        missing = REQUIRED_SLOTS[candidate] - present
        if missing:
            raise ValueError(f"structure_complete=true missing required slots: {sorted(missing)}")
    return value


def _require_text(value, fields):
    for field in fields:
        if not (value[field] or "").strip():
            raise ValueError(f"{field} must contain a concrete explanation")


def validate_goal_semantics(value, task="detection"):
    _validate_analyst_semantics(value, task)
    _require_text(value, ("label_justification",))
    if value["candidate"] is not None or value["mechanism_supports_goal"]:
        _require_text(value, ("conclusion_or_goal", "supporting_reason", "support_relation"))
    return value


def validate_counterargument_semantics(value, task="detection"):
    _validate_analyst_semantics(value, task)
    _require_text(value, ("label_justification",))
    if value["candidate"] is not None or value["failure_exposed"]:
        _require_text(value, ("challenged_inference", "decisive_counterargument"))
    _require_text(value, ("strongest_objection", "strongest_defense"))
    if value["winning_side"] == "objection" and value["verdict"] != "Fallacious":
        raise ValueError("An objection winner requires a positive verdict")
    if value["winning_side"] == "defense" and value["verdict"] != "Non-Fallacious":
        raise ValueError("A defense winner requires a negative verdict")
    return value


def validate_comparative_adjudicator_semantics(value, task, allowed_candidates):
    labels_for(task)
    selected = value["selected_candidate"]
    verdict = value["selected_verdict"]
    if selected is not None and selected not in allowed_candidates:
        raise ValueError("Final adjudicator selected a candidate outside the allowed set")
    if verdict == "Non-Fallacious" and selected is not None:
        raise ValueError("A negative verdict cannot select a fallacy candidate")
    if verdict == "Fallacious" and selected is None:
        raise ValueError("A positive verdict requires a fallacy candidate")
    if task == "classification" and verdict != "Fallacious":
        raise ValueError("Classification requires a fallacious verdict")
    _require_text(value, ("decision_reason", "decisive_condition"))
    return value


def validate_conflict_resolution_semantics(value, candidates):
    if value["loser_failure"] in candidates:
        raise ValueError(
            "loser_failure must explain the failure, not merely repeat a candidate label"
        )
    if len(value["loser_failure"].strip()) < 8:
        raise ValueError("loser_failure is too short to be explanatory")
    if len(value["decisive_test"].strip()) < 8:
        raise ValueError("decisive_test is too short")
    return value


def validate_arbiter_semantics(value, allowed_candidates, *, require_selection=False):
    selected = value["selected_candidate"]

    if selected is not None and selected not in allowed_candidates:
        raise ValueError("Arbiter selected a non-surviving candidate")
    if require_selection and selected is None:
        raise ValueError("Classification adjudicator must select one allowed candidate")

    _require_text(value, ("decision_reason", "decisive_condition"))
    return value


def validate_output(value, schema):
    _validate(value, schema, "$")
    return value


def _validate(value, schema, path):
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            try:
                _validate(value, option, path)
                matches += 1
            except ValueError:
                pass
        if matches != 1:
            raise ValueError(f"{path} must match exactly one schema (matched {matches})")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} must equal {schema['const']!r}")
    if "anyOf" in schema:
        failures = []
        for option in schema["anyOf"]:
            try:
                _validate(value, option, path)
                return
            except ValueError as exc:
                failures.append(str(exc))
        raise ValueError(f"{path} did not match allowed schemas: {failures[0]}")
    if "enum" in schema:
        if value not in schema["enum"]:
            raise ValueError(f"{path} must be one of {schema['enum']}")
        return
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be object")
        extra = set(value) - set(schema["properties"])
        missing = set(schema.get("required", [])) - set(value)
        if extra:
            raise ValueError(f"{path} has unexpected fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"{path} is missing fields: {sorted(missing)}")
        for key, child in schema["properties"].items():
            if key in value:
                _validate(value[key], child, f"{path}.{key}")
    elif expected == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path} must be array")
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 10**9):
            raise ValueError(f"{path} item count out of range")
        for index, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{index}]")
    elif expected == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path} must be string")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 10**9):
            raise ValueError(f"{path} length out of range")
    elif expected == "boolean":
        if type(value) is not bool:
            raise ValueError(f"{path} must be boolean")
    elif expected == "null":
        if value is not None:
            raise ValueError(f"{path} must be null")


def validate_evidence_spans(value, target):
    canonical = []
    for span in value.get("evidence_spans", []):
        if span.strip() and span in target:
            canonical.append(span)
            continue
        # Recover literal TARGET text when copying changed only whitespace.
        tokens = span.split()
        match = re.search(r"\s+".join(re.escape(token) for token in tokens), target) if tokens else None
        if match is None:
            raise ValueError(
                f"Evidence span not found in TARGET: {span!r}. "
                "Copy a short verbatim substring from input.target, not parent or a paraphrase."
            )
        canonical.append(match.group(0))
    if "evidence_spans" in value:
        value["evidence_spans"] = canonical
    return value
