"""Defender v2 contract and conservative adapter; no semantic truth claims."""
import json
from copy import deepcopy

from src.adversarial_schemas import defender_review_schema, _is_valid_substring
from src.schemas import validate_output


def validate_defender_review(value, target):
    validate_output(value, defender_review_schema())
    ca, alt = value['candidate_assessment'], value['alternative_assessment']
    for name, text in [('inference_summary', value['inference_summary']),
                       ('condition', ca['condition']), ('candidate explanation', ca['explanation']),
                       ('alternative explanation', alt['explanation']),
                       ('charitable_interpretation', value['charitable_interpretation'])]:
        if not text.strip():
            raise ValueError(f'Defender {name} must be non-empty')
    quotes = [value['premise_quote'], value['conclusion_quote'], value['counter_quote'],
              ca['evidence_quote'], alt['premise_quote'], alt['conclusion_quote']]
    for quote in quotes:
        if quote and not _is_valid_substring(quote, target):
            raise ValueError('Defender evidence must be a verbatim substring of target')
    if alt['class'] == 'None' and (alt['status'] != 'not_established'
                                  or alt['premise_quote'] or alt['conclusion_quote']):
        raise ValueError('Alternative None requires not_established and empty quotes')


def normalize_defender_review(prosecutor, review, target):
    validate_defender_review(review, target)
    raw = deepcopy(review)
    ca, alt = review['candidate_assessment'], review['alternative_assessment']
    submitted = effective = review['decision']
    reasons = []
    if submitted == 'challenge':
        if ca['status'] not in ('contradicted', 'not_established', 'secondary_mechanism'):
            reasons.append('candidate_not_rebutted')
        if not ca['condition'].strip() or not ca['explanation'].strip():
            reasons.append('missing_candidate_objection')
        if ca['status'] in ('contradicted', 'secondary_mechanism') and not ca['evidence_quote'].strip():
            reasons.append('missing_candidate_evidence')
        if alt['class'] == prosecutor['candidate_class']:
            reasons.append('same_class')
        if alt['class'] == 'None' or alt['status'] != 'supported':
            reasons.append('alternative_not_supported')
        if not (alt['premise_quote'].strip() or alt['conclusion_quote'].strip()) or not review['counter_quote'].strip():
            reasons.append('missing_alternative_evidence')
        if not review['decisive_difference'].strip():
            reasons.append('missing_decisive_difference')
        if reasons:
            effective = 'defer'
    challenge = effective == 'challenge'
    return {
        'concede_charge': not challenge,  # compatibility flag, not semantic agreement
        'alternative_class': alt['class'] if challenge else 'None',
        'counter_quote': review['counter_quote'],
        'charitable_interpretation': review['charitable_interpretation'],
        'raw_report': raw,
        'validation': {'policy': 'evidence_v2', 'schema_version': 'defender_review_v2',
                       'submitted_decision': submitted, 'effective_decision': effective,
                       'gate_reasons': reasons},
    }


def defender_v2_system_prompt():
    from src.adversarial_prompts import COMMON_ADVERSARIAL
    example = {
        'decision': 'challenge', 'premise_quote': 'One bad shop',
        'conclusion_quote': 'every shop is bad', 'inference_summary': 'One case is extended to all shops.',
        'candidate_assessment': {'status': 'not_established', 'condition': 'Consensus used as proof.',
            'evidence_quote': '', 'explanation': 'The target offers one case, not popular agreement.'},
        'alternative_assessment': {'class': 'Hasty Generalization', 'status': 'supported',
            'premise_quote': 'One bad shop', 'conclusion_quote': 'every shop is bad',
            'explanation': 'An individual shop is treated as representative of every shop.'},
        'decisive_difference': 'Case-to-population rather than consensus-to-truth.',
        'counter_quote': 'One bad shop proves every shop is bad',
        'charitable_interpretation': 'The missing consensus condition defeats the candidate; the sample leap supports HG.',
    }
    uphold = deepcopy(example)
    uphold.update(decision='uphold', counter_quote='', decisive_difference='No rival explains the inference better.',
                  charitable_interpretation='The candidate HG accounts for the main sample leap.')
    uphold['candidate_assessment'].update(status='supported', condition='A limited sample is extended to a group.',
        evidence_quote='One bad shop proves every shop is bad', explanation='The single case supports an all-shops conclusion.')
    uphold['alternative_assessment'] = {'class': 'None', 'status': 'not_established',
        'premise_quote': '', 'conclusion_quote': '', 'explanation': 'No better-supported competitor.'}
    defer = deepcopy(uphold)
    defer.update(decision='defer', decisive_difference='',
        charitable_interpretation='The available wording does not establish which mechanism is primary.')
    defer['candidate_assessment']['status'] = 'uncertain'
    return COMMON_ADVERSARIAL + (
        'You are the DEFENDER, an evidence-based diagnostic reviewer, not an advocate obliged to disagree. '
        'Classification only, eight CoCoLoFa labels. First reconstruct the main inference, then audit the candidate, '
        'then examine runner-up under the SAME standard; consider a third class only when needed. '
        'A plausible runner-up is not a reason to switch. Pinpoint a missing candidate condition, contradictory '
        'evidence, or a demonstrably secondary mechanism. Not seeing proof is not proof of a contradiction. '
        'Challenge only when a grounded alternative explains the MAIN inference better and a decisive difference '
        'is established. If both mechanisms are supported and primacy is unresolved, defer. Uphold when candidate '
        'survives comparison. Do not invent missing samples, warrants, or context.\n'
        'Majority vs HG: consensus as justification differs from a case-to-population leap. A case mentioned in context '
        'does not automatically serve as a representative sample. HG may use implicit cases or analogies only when '
        'grounded in supplied text; identify case and generalized group. Authority vs Nature: distinguish a source '
        'supporting a premise from naturalness justifying a value conclusion. Worse Problems vs False Dilemma: '
        'prioritizing or deferring A for B does not itself exclude alternatives. SS requires unsupported escalation, '
        'not future tense alone. Tradition requires longevity doing justificatory work, not a historical mention.\n'
        'All nonempty evidence quotes must be verbatim TARGET substrings; context resolves references only. Shared '
        'quotes are allowed; no regex keyword required. For implicit premises/conclusions use empty quotes plus '
        'an explicit explanation in inference_summary. For not_established explain the missing condition; do not '
        'fabricate a quote proving absence. For contradicted/secondary_mechanism cite target evidence.\n'
        'Return exactly one JSON object, no response/output wrapper, Markdown or additional fields. Every field '
        'below is required, including counter_quote for uphold/defer. Complete JSON examples for target '
        '"One bad shop proves every shop is bad":\n'
        'Candidate Majority, challenge example: ' + json.dumps(example) + '\n'
        'Candidate HG, uphold example: ' + json.dumps(uphold) + '\n'
        'Unresolved reading, defer format example (not a prescribed verdict for this target): ' + json.dumps(defer) + '\n'
        'The authoritative JSON schema (use only these enum values) is: ' + json.dumps(defender_review_schema())
    )
