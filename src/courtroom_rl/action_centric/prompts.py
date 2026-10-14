"""Keep original role behavior; remove only incompatible report contracts."""
from src.labels import FALLACIES
from src.courtroom_rl.vendor.baseline.adversarial_prompts import (
    PROSECUTOR_PROMPT_CLASSIFICATION, DEFENDER_PROMPT_CLASSIFICATION,
    ARBITER_PROMPT_CLASSIFICATION, DEFENDER_PROMPT)
from src.courtroom_rl.vendor.baseline.fallacy_patterns import get_pattern_enriched_definitions


def role_behavior(role):
    if role=='Prosecutor':
        return PROSECUTOR_PROMPT_CLASSIFICATION.split('INSTRUCTIONS:\n',1)[0].format(patterns=get_pattern_enriched_definitions())
    if role=='Defender':
        # Core charity/concession behavior + eight-class boundary verification;
        # neither the one-pass decision command nor output field names survive.
        charity=DEFENDER_PROMPT.split('OUTPUT DECISION:\n',1)[0]
        charity=charity.replace(' (set concede_charge=true)','')
        return charity+DEFENDER_PROMPT_CLASSIFICATION.split('OUTPUT DECISION:\n',1)[0]
    if role=='Judge':
        return ARBITER_PROMPT_CLASSIFICATION.split('DECISION PROTOCOL:\n',1)[0].format(allowed_labels=', '.join(FALLACIES))
    raise ValueError('Unknown courtroom role')
