import re

from src.io_utils import digest
from src.courtroom_rl.schemas import Claim


def evidence_key(spans,source,quote):
    if not spans:
        return [(source,quote)]
    return sorted((s['source'],s['start'],s['end'],s['quote']) for s in spans)


def validate_payload(payload, state, action, target):
    quote = payload.get('supported_quote')
    source = payload.get('source', 'comment')
    if source not in ('comment', 'parent_comment', 'title'):
        raise ValueError('Unknown quote source')
    text = getattr(state.case_input, source)
    if not isinstance(quote, str) or not quote.strip() or quote not in text:
        raise ValueError('supported_quote must be an exact nonempty source quote')
    if action in ('ACCUSE', 'REVISE_CHARGE') and source != 'comment':
        raise ValueError('Accusation quote must ground the target comment')
    if 'evidence_ids' in payload or 'evidence_spans' in payload:
        from src.courtroom_rl.evidence import passages_for, resolve_references
        expected = resolve_references(payload,passages_for(state.case_input,target_only=action in ('ACCUSE','REVISE_CHARGE')))
        if payload.get('evidence_spans') != expected['evidence_spans'] or quote != expected['supported_quote'] or source != expected['source']:
            raise ValueError('Evidence IDs, source, offsets and compatibility quote must agree')
    for span in payload.get('evidence_spans',[]):
        if span['source'] not in ('comment','parent_comment','title'):
            raise ValueError('Unknown evidence source')
        original = getattr(state.case_input,span['source'])
        start,end = span['start'],span['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(original) or original[start:end] != span['quote']:
            raise ValueError('Evidence offsets must resolve exactly to original text')
        if action in ('ACCUSE','REVISE_CHARGE') and span['source'] != 'comment':
            raise ValueError('Accusation evidence must ground the target comment')
    if payload.get('label') != target_label(state, action, target):
        raise ValueError('Output label differs from selected target')
    if not isinstance(payload.get('mechanism'), str) or not payload['mechanism'].strip():
        raise ValueError('Missing mechanism')
    if action == 'REVISE_CHARGE':
        normalized = ' '.join(payload['mechanism'].casefold().split())
        key = evidence_key(payload.get('evidence_spans',[]),source,quote)
        if any(c.author == 'Prosecutor' and evidence_key(c.evidence_spans,c.source_span['source'],c.source_span['quote']) == key
               and ' '.join(c.proposition.casefold().split()) == normalized for c in state.claims):
            raise ValueError('Revision requires a new grounded distinction, not only a new label')
    known = {c.claim_id for c in state.claims}
    attacks = payload.get('attacks_claim_ids', [])
    if not isinstance(attacks, list) or any(i not in known for i in attacks):
        raise ValueError('Unknown attacked claim')
    if action == 'CHALLENGE' and target not in attacks:
        raise ValueError('Challenge must attack selected claim')
    if state.pending_request and payload.get('answer_to_pending_request') != state.pending_request[1]:
        raise ValueError('Reply must answer pending request')


def target_label(state, action, target):
    if action in ('ACCUSE', 'REVISE_CHARGE', 'PROPOSE_ALTERNATIVE'):
        return target
    return next(c.label for c in state.claims if c.claim_id == target)


def insert_claim(state, action, payload):
    quote, source = payload['supported_quote'], payload.get('source', 'comment')
    normalized = re.sub(r'\s+', ' ', payload['mechanism'].casefold()).strip()
    spans = payload.get('evidence_spans',[])
    key = evidence_key(spans,source,quote)
    fingerprint = digest([normalized,payload['label'],key,state.active_role,action]) if spans else digest([normalized, payload['label'], source, quote, state.active_role, action])
    if any(c.normalized_fingerprint == fingerprint for c in state.claims):
        raise ValueError('Duplicate claim under identical evidence/relation')
    start = spans[0]['start'] if spans else getattr(state.case_input, source).index(quote)
    relation = 'alternative' if action == 'PROPOSE_ALTERNATIVE' else 'accusation'
    from src.courtroom_rl.observation import frozen_text
    embedding = frozen_text(normalized)
    candidates = [c.claim_id for c in state.claims if c.author == state.active_role and c.label == payload['label']
                  and c.relation == relation and evidence_key(c.evidence_spans,c.source_span['source'],c.source_span['quote']) == key
                  and float(embedding @ frozen_text(c.proposition)) >= .90]
    claim = Claim(f'C{len(state.claims)+1}', state.active_role, payload['label'], payload['mechanism'],
                  {'source': source, 'quote': quote, 'start': start, 'end': start+len(quote)},
                  attacks_ids=payload.get('attacks_claim_ids', []),
                  normalized_fingerprint=fingerprint, created_step=state.decision_count,
                  relation=relation, similarity_review_candidates=candidates,evidence_spans=spans)
    state.claims.append(claim)
    return claim
