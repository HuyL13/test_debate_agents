"""Proposal 2: a bounded proposal/critique/verification protocol, without RL claims.

Opening review is distinct from deciding to switch labels. The final verifier
is not forced to retain the first speaker's label on disagreement or abstention.
"""
from copy import deepcopy
import json
import math

from src import aligned_classification as aligned
from src.labels import FALLACIES

PROFILE = 'proposal_2'
VERSION = 'evidence_game_v1'
ACTIONS = ('uphold', 'request_comparison', 'objection_only', 'insufficient_evidence')


def defender_schema():
    schema = deepcopy(aligned.defender_schema())
    del schema['properties']['decision']
    schema['properties']['action'] = aligned.enum(ACTIONS)
    schema['required'] = list(schema['properties'])
    return schema


def arbiter_schema(allowed):
    schema = deepcopy(aligned.arbiter_schema(allowed))
    schema['properties']['probabilities'] = aligned.obj({
        label: {'type': 'number', 'minimum': 0.0, 'maximum': 1.0} for label in FALLACIES})
    schema['required'] = list(schema['properties'])
    return schema


def usable_alternative(review):
    alt = review['alternative_assessment']
    return alt['class'] != 'None' and alt['condition_status'] in ('supported', 'uncertain') and bool(aligned._quote(alt))


def validate_defender(value, target, candidate):
    aligned.validate_defender(value, target, candidate, schema=defender_schema())
    action = value['action']
    if action == 'uphold' and value['candidate_assessment']['condition_status'] != 'supported':
        raise ValueError('Uphold requires a supported candidate assessment')
    if action in ('request_comparison', 'objection_only') and not value['candidate_objection'].strip():
        raise ValueError('Review action requires a concrete candidate objection')
    if action == 'request_comparison' and not usable_alternative(value):
        raise ValueError('Comparison requires a grounded supported or uncertain alternative')
    if action == 'insufficient_evidence' and not value['unresolved_commitment'].strip():
        raise ValueError('Insufficient evidence must identify an unresolved textual commitment')


def validate_arbiter(value, target, allowed):
    aligned.validate_output(value, arbiter_schema(allowed))
    ordinary = {k: v for k, v in value.items() if k != 'probabilities'}
    aligned.validate_arbiter(ordinary, target, allowed)
    probs = value['probabilities']
    if any(type(p) not in (int, float) or not math.isfinite(p) for p in probs.values()):
        raise ValueError('Forecast probabilities must be finite numbers')
    if not math.isclose(sum(probs.values()), 1.0, abs_tol=1e-6):
        raise ValueError('Eight-class probabilities must sum to one')
    chosen = value['prediction']
    if probs[chosen] + 1e-6 < max(probs[label] for label in allowed):
        raise ValueError('Chosen label must maximize probability among offered options')
    if not math.isclose(value['confidence'], probs[chosen], abs_tol=1e-6):
        raise ValueError('Confidence must equal the unconditional probability of the chosen class')


def system_prompt(role, schema):
    if role == 'Prosecutor':
        # Byte-identical Prosecutor request across proposals for paired replay.
        return aligned.system_prompt(role, schema)
    if role == 'Defender':
        instructions = (
            'You are the DEFENDER in a bounded evidence-review game. Your objective is useful, checkable '
            'criticism that improves classification, not disagreement, silence or winning the judge. '
            'Reconstruct the disputed step independently of the indictment and assess both labels with '
            'identical fields. Opening review is NOT a decision to switch labels.\n'
            'ACTIONS: uphold only when the candidate is supported after comparison; request_comparison '
            'when a concrete objection and a grounded supported/uncertain alternative warrant verification, '
            'even if decisive_difference is not yet resolved; objection_only when a concrete candidate flaw '
            'is identified but no adequate alternative is available; insufficient_evidence only when you '
            'name the unresolved textual commitment. No action wins automatically or preserves a label by fiat. '
            'Do not manufacture an alternative or require certainty before raising a grounded question. '
            'Condition support and primary/secondary role are separate. Preserve licensed implicit warrants. '
            'Example: one incident -> widespread corruption raises HG vs SS for verification if the alleged '
            'escalation has not been identified. Point out missing transitions; do not invent them. '
            'A famous artist as an example does not automatically supply authority-to-truth reasoning. '
            'Return a concise criticism focused on the inferential step, not an extended persuasive speech.'
        )
    else:
        instructions = (
            'You are the DIALECTICAL ARBITER, the verifier of an evidence-review game. '
            'Verify every claim against full TARGET and supplied context; reports are claims to check, '
            'not testimony to summarize. Both anonymous options have equal burden and no role has veto. '
            'An objection requests scrutiny, not an automatic switch. Silence, uphold and uncertainty '
            'do not prove the initial label. Inspect all defining conditions, the actual disputed step, '
            'and whether an option imports premises, choices or escalation. Explain the selected and '
            'rejected diagnosis. Ignore speaking order, rhetorical force, verbosity and self-confidence. '
            'Choose only from the offered classes. If neither is established use both_unsupported; '
            'if primacy is unresolved use unresolved. Still make an honest forced benchmark choice. '
            'Report unconditional probabilities across ALL EIGHT classes, summing to one; do not '
            'renormalize to the two offered options. Probability outside the candidate set is allowed '
            'and records coverage limitations. Choose the most probable OFFERED label and set confidence '
            'to its unconditional probability. These forecasts are uncalibrated diagnostics until evaluated; '
            'they are not votes or an automatic evidence gate.'
        )
    return aligned.common_prompt() + instructions + '\nOUTPUT CONTRACT:\n' + json.dumps(schema)


def normalize_review(review):
    action = review['action']
    requested = action == 'request_comparison'
    return {'concede_charge': not requested,
            'alternative_class': review['alternative_assessment']['class'] if requested else 'None',
            'counter_quote': aligned._quote(review['alternative_assessment']) if requested else '',
            'charitable_interpretation': review['comparison'], 'raw_report': deepcopy(review),
            'validation': {'policy': PROFILE, 'schema_version': VERSION,
                           'submitted_decision': action, 'effective_decision': action, 'gate_reasons': []}}


def execute(ask, model_input):
    target = model_input.comment
    prosecutor = ask('Prosecutor', 'indictment', {}, [],
        'Reconstruct the disputed inferential step; commit to a ranked candidate and runner-up with missing conditions.',
        schema=aligned.prosecutor_schema(), validator=lambda v: aligned.validate_prosecutor(v, target))
    review = ask('Defender', 'plea', {'prosecutor_indictment': prosecutor}, [],
        'Inspect the candidate. Raise a grounded question without requiring a proven replacement; name unresolved commitments.',
        schema=defender_schema(), validator=lambda v: validate_defender(v, target, prosecutor['candidate_class']))
    defender = normalize_review(review)
    comparison = deepcopy(review)
    from_review = usable_alternative(review)
    if not from_review:
        # A pass/objection cannot hide the already committed runner-up. Missing
        # support remains explicit; inclusion does not certify it as a fallacy.
        comparison['alternative_assessment'] = deepcopy(prosecutor['runner_up_assessment'])
    options = aligned.dossiers(prosecutor, comparison, True)
    # Canonical order independent of role or arrival time. This is not claimed
    # to eliminate class/order bias; swap sensitivity is audited separately.
    options.sort(key=lambda option: option['class'])
    allowed = [o['class'] for o in options]
    verdict = ask('DialecticalArbiter', 'verification', {'options': options}, [],
        'Independently verify both dossiers; no default winner. Choose exactly one of: ' + json.dumps(allowed),
        schema=arbiter_schema(allowed), validator=lambda v: validate_arbiter(v, target, allowed))
    arbiter = {**verdict, 'selection_policy': 'verified_comparison',
               'uncertainty': verdict['resolution'] != 'selected',
               'game_trace': {'version': VERSION, 'defender_action': review['action'],
                   'candidate_classes': allowed, 'alternative_from_review': from_review,
                   'outside_candidate_mass': sum(p for label, p in verdict['probabilities'].items() if label not in allowed),
                   'decision_overrode_initial': verdict['prediction'] != prosecutor['candidate_class'],
                   'forecast_note': 'Uncalibrated eight-class report; not an independent probability source.',
                   'nominal_calls': 3, 'rebuttal_rounds': 0}}
    return prosecutor, defender, arbiter, 'verified_comparison'
