"""Shared JSON validation and quote normalization."""
import math
from jsonschema import Draft202012Validator
from src.labels import labels_for

def object_schema(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}

def report_schema(task):
    return object_schema({'prediction': {'type': 'string', 'enum': list(labels_for(task))},
                          'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                          'content': {'type': 'string'}})

def _normalize_quote_text(text):
    for dash in ('\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2212'):
        text = text.replace(dash, '-')
    for quote in ('\u2018', '\u2019', '\u201a', '\u201b'):
        text = text.replace(quote, "'")
    for quote in ('\u201c', '\u201d', '\u201e', '\u201f'):
        text = text.replace(quote, '"')
    return ' '.join(text.split())

def validate_output(value, schema):
    def finite(item):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Non-finite JSON number')
        if isinstance(item, dict):
            for sub in item.values():
                finite(sub)
        elif isinstance(item, list):
            for sub in item:
                finite(sub)
    finite(value)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    if errors:
        raise ValueError('Output does not match schema: ' + errors[0].message)
