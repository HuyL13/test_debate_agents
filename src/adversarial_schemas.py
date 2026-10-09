"""JSON Schemas and validators for Adversarial Dialectical Debate roles."""

from typing import Any, Dict
from src.labels import FALLACIES, labels_for


def prosecutor_schema() -> Dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'has_fallacy_charge': {'type': 'boolean'},
            'candidate_class': {
                'type': 'string',
                'enum': list(FALLACIES) + ['None'],
            },
            'defect_mechanism': {'type': 'string'},
            'quote': {'type': 'string'},
        },
        'required': ['has_fallacy_charge', 'candidate_class', 'defect_mechanism', 'quote'],
    }


def defender_schema() -> Dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'concede_charge': {'type': 'boolean'},
            'charitable_interpretation': {'type': 'string'},
            'counter_quote': {'type': 'string'},
        },
        'required': ['concede_charge', 'charitable_interpretation', 'counter_quote'],
    }


def dialectical_arbiter_schema(task: str) -> Dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'prediction': {
                'type': 'string',
                'enum': list(labels_for(task)),
            },
            'confidence': {
                'type': 'number',
                'minimum': 0.0,
                'maximum': 1.0,
            },
            'content': {'type': 'string'},
        },
        'required': ['prediction', 'confidence', 'content'],
    }


from src.schemas import _normalize_quote_text


def validate_prosecutor(value: Any, target_comment: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Prosecutor output must be a dict")
    if not isinstance(value.get('has_fallacy_charge'), bool):
        raise ValueError("has_fallacy_charge must be boolean")
    cand = value.get('candidate_class')
    if cand not in list(FALLACIES) + ['None']:
        raise ValueError(f"Invalid candidate_class: {cand}")
    if value['has_fallacy_charge']:
        if cand == 'None':
            raise ValueError("candidate_class cannot be 'None' when has_fallacy_charge is true")
        quote = value.get('quote', '')
        if quote and _normalize_quote_text(quote).casefold() not in _normalize_quote_text(target_comment).casefold():
            raise ValueError(f"Prosecutor quote '{quote}' is not a verbatim substring of target comment")


def validate_defender(value: Any, target_comment: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Defender output must be a dict")
    if not isinstance(value.get('concede_charge'), bool):
        raise ValueError("concede_charge must be boolean")
    if not isinstance(value.get('charitable_interpretation'), str):
        raise ValueError("charitable_interpretation must be a string")


def validate_dialectical_arbiter(value: Any, task: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Arbiter output must be a dict")
    allowed = labels_for(task)
    if value.get('prediction') not in allowed:
        raise ValueError(f"Arbiter prediction must be one of {allowed}")
    conf = value.get('confidence')
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        raise ValueError("Arbiter confidence must be a float between 0.0 and 1.0")
    if not isinstance(value.get('content'), str) or not value['content'].strip():
        raise ValueError("Arbiter content must be a non-empty string")
