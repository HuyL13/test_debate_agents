"""JSON Schemas and validators for Adversarial Dialectical Debate roles."""

import math
from typing import Any, Dict
from src.data.loader import ModelInput
from src.labels import FALLACIES, labels_for, normalize_fallacy_name
from src.schemas import _normalize_quote_text


def _extract_target_text(target: Any) -> str:
    """Extract target comment text from either a ModelInput or string."""
    if isinstance(target, ModelInput):
        return target.comment or ""
    return str(target) if target is not None else ""


def _is_valid_substring(quote: str, target: str) -> bool:
    """Check if quote is a verbatim substring of target after whitespace/punctuation normalization."""
    if not quote or not target:
        return False
    norm_quote = _normalize_quote_text(quote).casefold()
    norm_target = _normalize_quote_text(target).casefold()
    return norm_quote in norm_target


def prosecutor_schema(task: str = 'detection') -> Dict[str, Any]:
    if task == 'classification':
        return {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'has_fallacy_charge': {'type': 'boolean'},
                'candidate_class': {
                    'type': 'string',
                    'enum': list(FALLACIES),
                },
                'defect_mechanism': {'type': 'string'},
                'quote': {'type': 'string'},
                'runner_up_class': {
                    'type': 'string',
                    'enum': list(FALLACIES),
                },
                'runner_up_defect': {'type': 'string'},
                'runner_up_quote': {'type': 'string'},
            },
            'required': [
                'has_fallacy_charge', 'candidate_class', 'defect_mechanism', 'quote',
                'runner_up_class', 'runner_up_defect', 'runner_up_quote',
            ],
        }
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


def defender_schema(task: str = 'detection') -> Dict[str, Any]:
    if task == 'classification':
        return {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'concede_charge': {'type': 'boolean'},
                'alternative_class': {
                    'type': 'string',
                    'enum': list(FALLACIES) + ['None'],
                },
                'charitable_interpretation': {'type': 'string'},
                'counter_quote': {'type': 'string'},
            },
            'required': ['concede_charge', 'alternative_class', 'charitable_interpretation', 'counter_quote'],
        }
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
            'reasoning': {'type': 'string'},
        },
        'required': ['prediction', 'confidence', 'content'],
    }


def arbiter_pairwise_schema(opt1: str, opt2: str) -> Dict[str, Any]:
    allowed = list(dict.fromkeys([opt1, opt2]))
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'prediction': {
                'type': 'string',
                'enum': allowed,
            },
            'confidence': {
                'type': 'number',
                'minimum': 0.0,
                'maximum': 1.0,
            },
            'content': {'type': 'string'},
            'reasoning': {'type': 'string'},
        },
        'required': ['prediction', 'confidence', 'content'],
    }


def validate_prosecutor(value: Any, target_comment: Any, task: str = 'detection') -> None:
    if not isinstance(value, dict):
        raise ValueError("Prosecutor output must be a dict")
    charge = value.get('has_fallacy_charge')
    if type(charge) is not bool:
        raise ValueError("has_fallacy_charge must be boolean")

    cand = value.get('candidate_class')
    target_text = _extract_target_text(target_comment)

    if task == 'classification':
        if not charge:
            raise ValueError("has_fallacy_charge must be true for classification task")
        allowed = list(FALLACIES)
        if cand not in allowed:
            raise ValueError(f"Invalid candidate_class: {cand}")

        defect = value.get('defect_mechanism')
        if not isinstance(defect, str) or not defect.strip():
            raise ValueError("Prosecutor defect_mechanism must be a non-empty string")

        quote = value.get('quote')
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError("Prosecutor quote must be non-empty for classification task")
        if not _is_valid_substring(quote, target_text):
            raise ValueError(
                f"Prosecutor quote '{quote}' is not a verbatim substring of target comment. "
                f"Do NOT quote from parent comment or article! Quote strictly from target comment: '{target_text[:100]}...'"
            )

        ru_cand = value.get('runner_up_class')
        if ru_cand not in list(FALLACIES):
            norm = normalize_fallacy_name(ru_cand)
            if norm and norm in list(FALLACIES):
                ru_cand = norm
                value['runner_up_class'] = norm
            else:
                raise ValueError(f"Invalid runner_up_class: {ru_cand}")
        if ru_cand == cand:
            raise ValueError("runner_up_class must be different from candidate_class")

        ru_defect = value.get('runner_up_defect')
        if not isinstance(ru_defect, str) or not ru_defect.strip():
            raise ValueError("Prosecutor runner_up_defect must be a non-empty string")

        ru_quote = value.get('runner_up_quote')
        if not isinstance(ru_quote, str) or not ru_quote.strip():
            raise ValueError("Prosecutor runner_up_quote must be non-empty for classification task")
        if not _is_valid_substring(ru_quote, target_text):
            raise ValueError(
                f"Prosecutor runner_up_quote '{ru_quote}' is not a verbatim substring of target comment. "
                f"Do NOT quote from parent comment or article! Quote strictly from target comment: '{target_text[:100]}...'"
            )

    else:  # detection task
        defect = value.get('defect_mechanism')
        if not isinstance(defect, str) or not defect.strip():
            raise ValueError("Prosecutor defect_mechanism must be a non-empty string")

        if charge:
            if cand == 'None':
                raise ValueError("candidate_class cannot be 'None' when has_fallacy_charge is true")
            if cand not in list(FALLACIES):
                raise ValueError(f"Invalid candidate_class: {cand}")

            quote = value.get('quote')
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError("Prosecutor quote must be non-empty when has_fallacy_charge is true")
            if not _is_valid_substring(quote, target_text):
                raise ValueError(
                    f"Prosecutor quote '{quote}' is not a verbatim substring of target comment. "
                    f"Do NOT quote from parent comment or article! Quote strictly from target comment: '{target_text[:100]}...'"
                )
        else:
            if cand != 'None':
                raise ValueError(f"candidate_class must be 'None' when has_fallacy_charge is false, got '{cand}'")
            quote = value.get('quote')
            if quote is not None and str(quote).strip() != '':
                raise ValueError(f"quote must be empty when has_fallacy_charge is false, got '{quote}'")


def validate_defender(value: Any, target_comment: Any, task: str = 'detection') -> None:
    if not isinstance(value, dict):
        raise ValueError("Defender output must be a dict")
    concede = value.get('concede_charge')
    if type(concede) is not bool:
        raise ValueError("concede_charge must be boolean")

    interp = value.get('charitable_interpretation')
    if not isinstance(interp, str) or not interp.strip():
        raise ValueError("Defender charitable_interpretation must be a non-empty string")

    target_text = _extract_target_text(target_comment)
    c_quote = value.get('counter_quote', '')
    if c_quote is None:
        c_quote = ''

    if task == 'classification':
        alt = value.get('alternative_class')
        if alt not in list(FALLACIES) + ['None']:
            norm = normalize_fallacy_name(alt)
            if norm and norm in list(FALLACIES) + ['None']:
                value['alternative_class'] = norm
                alt = norm
            else:
                for f in list(FALLACIES) + ['None']:
                    if isinstance(alt, str) and alt.casefold() == f.casefold():
                        value['alternative_class'] = f
                        alt = f
                        break

        if concede:
            value['alternative_class'] = 'None'
            if value.get('counter_quote') == 'None':
                value['counter_quote'] = ''
        else:
            if alt == 'None' or alt not in list(FALLACIES):
                raise ValueError("If concede_charge is false, alternative_class MUST be one of the eight fallacies (cannot be None)")
            if not isinstance(c_quote, str) or not c_quote.strip():
                raise ValueError("If concede_charge is false, counter_quote must be non-empty")
            if not _is_valid_substring(c_quote, target_text):
                raise ValueError(
                    f"Defender counter_quote '{c_quote}' is not a verbatim substring of target comment. "
                    f"Quote strictly from target comment evidence! "
                    f"If the target comment does not contain evidence for a competing class, set concede_charge=true."
                )

    elif not concede:  # detection task without concession
        if not isinstance(c_quote, str) or not c_quote.strip():
            raise ValueError("If concede_charge is false, counter_quote must be non-empty")
        if not _is_valid_substring(c_quote, target_text):
            raise ValueError(
                f"Defender counter_quote '{c_quote}' is not a verbatim substring of target comment. "
                f"Quote strictly from target comment evidence!"
            )


def _validate_confidence(conf: Any) -> float:
    if type(conf) is bool or not isinstance(conf, (int, float)):
        raise ValueError("Arbiter confidence must be a finite float between 0.0 and 1.0, and cannot be boolean")
    if math.isnan(conf) or math.isinf(conf) or not (0.0 <= conf <= 1.0):
        raise ValueError("Arbiter confidence must be a finite float between 0.0 and 1.0")
    return float(conf)


def validate_dialectical_arbiter(value: Any, task: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Arbiter output must be a dict")
    allowed = labels_for(task)
    if value.get('prediction') not in allowed:
        raise ValueError(f"Arbiter prediction must be one of {allowed}")

    _validate_confidence(value.get('confidence'))

    if ('content' not in value or not value['content']) and 'reasoning' in value and value['reasoning']:
        value['content'] = value['reasoning'] if isinstance(value['reasoning'], str) else str(value['reasoning'])

    content = value.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Arbiter content must be a non-empty string")


def validate_arbiter_pairwise(value: Any, opt1: str, opt2: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Arbiter output must be a dict")
    allowed = [opt1, opt2]
    if value.get('prediction') not in allowed:
        raise ValueError(f"Arbiter prediction must be one of {allowed}, got {value.get('prediction')}")

    _validate_confidence(value.get('confidence'))

    if ('content' not in value or not value['content']) and 'reasoning' in value and value['reasoning']:
        value['content'] = value['reasoning'] if isinstance(value['reasoning'], str) else str(value['reasoning'])

    content = value.get('content')
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Arbiter content must be a non-empty string")


def defender_review_schema() -> Dict[str, Any]:
    """Versioned evidence-review contract; v1 and detection schemas stay unchanged."""
    def obj(properties):
        return {'type': 'object', 'additionalProperties': False,
                'properties': properties, 'required': list(properties)}
    string = {'type': 'string'}
    return obj({
        'decision': {'type': 'string', 'enum': ['uphold', 'challenge', 'defer']},
        'premise_quote': string, 'conclusion_quote': string, 'inference_summary': string,
        'candidate_assessment': obj({
            'status': {'type': 'string', 'enum': ['supported', 'contradicted', 'not_established', 'secondary_mechanism', 'uncertain']},
            'condition': string, 'evidence_quote': string, 'explanation': string,
        }),
        'alternative_assessment': obj({
            'class': {'type': 'string', 'enum': list(FALLACIES) + ['None']},
            'status': {'type': 'string', 'enum': ['supported', 'not_established', 'uncertain']},
            'premise_quote': string, 'conclusion_quote': string, 'explanation': string,
        }),
        'decisive_difference': string, 'counter_quote': string, 'charitable_interpretation': string,
    })
