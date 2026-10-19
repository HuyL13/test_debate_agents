"""JSON Schemas and validators for Adversarial Dialectical Debate roles."""

from typing import Any, Dict
from src.labels import FALLACIES, labels_for


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
        'required': ['prediction', 'confidence'],
    }


import difflib
from src.schemas import _normalize_quote_text


def _find_best_verbatim_span(quote: str, text: str, min_ratio: float = 0.75):
    if not quote or not text:
        return None
    clean_quote = _normalize_quote_text(quote).strip()
    clean_text = _normalize_quote_text(text).strip()
    if not clean_quote or not clean_text:
        return None

    q_lower = clean_quote.casefold()
    t_lower = clean_text.casefold()
    if q_lower in t_lower:
        idx = t_lower.find(q_lower)
        return clean_text[idx:idx + len(clean_quote)]

    quote_words = clean_quote.split()
    if not quote_words:
        return None
    text_words = clean_text.split()
    n = len(quote_words)

    best_span = None
    best_ratio = 0.0
    for w_len in range(max(1, n - 2), min(len(text_words) + 1, n + 3)):
        for i in range(len(text_words) - w_len + 1):
            window = ' '.join(text_words[i:i + w_len])
            ratio = difflib.SequenceMatcher(None, q_lower, window.casefold()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_span = window

    if best_ratio >= min_ratio:
        return best_span
    return None


def validate_prosecutor(value: Any, target_comment: str, task: str = 'detection') -> None:
    if not isinstance(value, dict):
        raise ValueError("Prosecutor output must be a dict")
    if not isinstance(value.get('has_fallacy_charge'), bool):
        raise ValueError("has_fallacy_charge must be boolean")
    cand = value.get('candidate_class')
    allowed = list(FALLACIES) if task == 'classification' else list(FALLACIES) + ['None']
    if cand not in allowed:
        raise ValueError(f"Invalid candidate_class: {cand}")
    if task == 'classification' and not value.get('has_fallacy_charge'):
        raise ValueError("has_fallacy_charge must be true for classification task")
    if value.get('has_fallacy_charge'):
        if cand == 'None':
            raise ValueError("candidate_class cannot be 'None' when has_fallacy_charge is true")
        quote = value.get('quote', '')
        if quote and _normalize_quote_text(quote).casefold() not in _normalize_quote_text(target_comment).casefold():
            span = _find_best_verbatim_span(quote, target_comment)
            if span:
                value['quote'] = span
                quote = span
            else:
                raise ValueError(f"Prosecutor quote '{quote}' is not a verbatim substring of target comment. Do NOT quote from parent comment or article! Quote strictly from target comment: '{target_comment[:100]}...'")
        if task == 'classification':
            if not quote or not quote.strip():
                raise ValueError("Prosecutor quote must be non-empty for classification task")
            ru_cand = value.get('runner_up_class')
            if ru_cand not in list(FALLACIES):
                raise ValueError(f"Invalid runner_up_class: {ru_cand}")
            if ru_cand == cand:
                raise ValueError("runner_up_class must be different from candidate_class")
            ru_defect = value.get('runner_up_defect', '')
            if not isinstance(ru_defect, str) or not ru_defect.strip():
                raise ValueError("Prosecutor runner_up_defect must be a non-empty string")
            ru_quote = value.get('runner_up_quote', '')
            if not ru_quote or not ru_quote.strip():
                raise ValueError("Prosecutor runner_up_quote must be non-empty for classification task")
            if _normalize_quote_text(ru_quote).casefold() not in _normalize_quote_text(target_comment).casefold():
                span = _find_best_verbatim_span(ru_quote, target_comment)
                if span:
                    value['runner_up_quote'] = span
                else:
                    raise ValueError(f"Prosecutor runner_up_quote '{ru_quote}' is not a verbatim substring of target comment. Do NOT quote from parent comment or article! Quote strictly from target comment: '{target_comment[:100]}...'")


def validate_defender(value: Any, target_comment: Any, task: str = 'detection') -> None:
    if not isinstance(value, dict):
        raise ValueError("Defender output must be a dict")
    if not isinstance(value.get('concede_charge'), bool):
        raise ValueError("concede_charge must be boolean")
    if not isinstance(value.get('charitable_interpretation'), str):
        raise ValueError("charitable_interpretation must be a string")
    if task == 'classification':
        alt = value.get('alternative_class')
        concede = value.get('concede_charge')
        c_quote = value.get('counter_quote', '')
        if alt not in list(FALLACIES) + ['None']:
            for f in list(FALLACIES) + ['None']:
                if isinstance(alt, str) and alt.casefold() == f.casefold():
                    value['alternative_class'] = f
                    alt = f
                    break
        if alt not in list(FALLACIES) + ['None']:
            raise ValueError(f"Invalid alternative_class: {alt}")
        if not concede and alt == 'None':
            interp = value.get('charitable_interpretation', '').lower()
            if (not c_quote or not c_quote.strip()) or \
               'correctly identifies' in interp or \
               'supports this classification' in interp or \
               'no superior alternative' in interp or \
               'concurs' in interp:
                value['concede_charge'] = True
                concede = True
        if not concede:
            if alt not in list(FALLACIES):
                raise ValueError("If concede_charge is false, alternative_class MUST be one of the eight fallacies (cannot be None)")
            if not c_quote or not c_quote.strip():
                raise ValueError("If concede_charge is false, counter_quote must be non-empty")
            norm_quote = _normalize_quote_text(c_quote).casefold()
            from src.data.loader import ModelInput
            if isinstance(target_comment, ModelInput):
                all_texts = [target_comment.comment, target_comment.parent_comment, target_comment.title]
                if target_comment.article:
                    all_texts.append(target_comment.article)
                full_corpus = " ".join(_normalize_quote_text(t).casefold() for t in all_texts if t)
            else:
                full_corpus = _normalize_quote_text(str(target_comment)).casefold()
            if norm_quote not in full_corpus:
                span = _find_best_verbatim_span(c_quote, full_corpus)
                if span:
                    value['counter_quote'] = span
                else:
                    raise ValueError(
                        f"Defender counter_quote '{c_quote}' is not a verbatim substring of supplied context. "
                        f"Quote strictly from supplied text evidence! "
                        f"If the target comment or context does not contain evidence for a competing class, set concede_charge=true."
                    )


def validate_dialectical_arbiter(value: Any, task: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Arbiter output must be a dict")
    allowed = labels_for(task)
    if value.get('prediction') not in allowed:
        raise ValueError(f"Arbiter prediction must be one of {allowed}")
    conf = value.get('confidence')
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        raise ValueError("Arbiter confidence must be a float between 0.0 and 1.0")
    if ('content' not in value or not value['content']) and 'reasoning' in value and value['reasoning']:
        value['content'] = value['reasoning'] if isinstance(value['reasoning'], str) else str(value['reasoning'])
    if not isinstance(value.get('content'), str) or not value['content'].strip():
        raise ValueError("Arbiter content must be a non-empty string")


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
        'required': ['prediction', 'confidence'],
    }


def validate_arbiter_pairwise(value: Any, opt1: str, opt2: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("Arbiter output must be a dict")
    allowed = [opt1, opt2]
    if value.get('prediction') not in allowed:
        raise ValueError(f"Arbiter prediction must be one of {allowed}, got {value.get('prediction')}")
    conf = value.get('confidence')
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        raise ValueError("Arbiter confidence must be a float between 0.0 and 1.0")
    if ('content' not in value or not value['content']) and 'reasoning' in value and value['reasoning']:
        value['content'] = value['reasoning'] if isinstance(value['reasoning'], str) else str(value['reasoning'])
    if not isinstance(value.get('content'), str) or not value['content'].strip():
        raise ValueError("Arbiter content must be a non-empty string")

