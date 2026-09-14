from src.labels import FALLACIES, labels_for


RELATIONS = (
    "sample_to_population",
    "event_to_consequence",
    "consequence_progression",
    "alternatives_to_choice",
    "authority_to_claim",
    "popularity_to_claim",
    "nature_to_value",
    "tradition_to_preservation",
    "worse_problem_to_deprioritization",
    "other",
    "none",
)

CRITERIA = (
    "sample_to_population",
    "consequence_progression",
    "exhaustiveness_commitment",
    "authority_justification",
    "popularity_justification",
    "nature_to_value",
    "tradition_to_preservation",
    "worse_problem_deprioritization",
    "target_fallacy_condition",
    "none",
)


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


def scheme_schema(task):
    return object_schema({
        "candidate": _candidate(task),
        "evidence_spans": _spans(),
        "relation": {"enum": list(RELATIONS)},
        "structure_complete": {"type": "boolean"},
    })


def enthymeme_schema(task):
    return object_schema({
        "candidate": _candidate(task),
        "evidence_spans": _spans(),
        "required_assumption": {"anyOf": [_string(), {"type": "null"}]},
        "assumption_licensed": {"type": "boolean"},
    })


def critical_schema(task):
    return object_schema({
        "candidate": _candidate(task),
        "evidence_spans": _spans(),
        "criterion": {"enum": list(CRITERIA)},
        "criterion_met": {"type": "boolean"},
        "alternative_reading": {"anyOf": [_string(), {"type": "null"}]},
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


def arbiter_schema(task):
    return object_schema({
        "prediction": {"enum": list(labels_for(task))},
        "evidence_spans": _spans(),
    })


def validate_output(value, schema):
    _validate(value, schema, "$")
    return value


def _validate(value, schema, path):
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
    for span in value.get("evidence_spans", []):
        if span not in target:
            raise ValueError(f"Evidence span not found in TARGET: {span}")
    return value
