"""Transactional ledger adapter around existing evidence IDs and quote checks."""
from copy import deepcopy
from src.labels import FALLACIES
from src.courtroom_rl.evidence import passages_for, resolve_references
from src.courtroom_rl.action_centric.state import Hypothesis, Claim


def eligible(state,action):
    claims=[c for c in state.claims if c.status not in ('CONCEDED','CLOSED','RESOLVED')]
    if action=='CHALLENGE': candidates=[c.claim_id for c in claims if c.challenge_count==0 and c.author!='Defender']
    elif action=='SUPPORT': candidates=[c.claim_id for c in claims if c.response_count==0 and c.status=='DISPUTED']
    elif action=='CONCEDE': candidates=[c.claim_id for c in claims if c.author!='Defender']
    elif action=='REVISE': candidates=[h.id for h in state.hypotheses if h.visits<2 and h.status!='REJECTED']
    else:return []
    return [target for target in candidates if [action,target] not in state.invalid_targets]


def grounded(state,value,target_only=False):
    result=resolve_references(value,passages_for(state.case_input,target_only=target_only))
    mechanism=result.get('mechanism')
    if not isinstance(mechanism,str) or not mechanism.strip() or len(mechanism)>2000:
        raise ValueError('Missing or oversized grounded mechanism')
    return result


def evidence_keys(value):
    return [(s['source'],s['start'],s['end']) for s in value.get('evidence_spans',[])]


def append_claim(state,hypothesis,value,role,kind,budget):
    if len(state.claims)>=budget.max_claims: raise ValueError('Claim capacity exhausted')
    normalized=' '.join(value['mechanism'].casefold().split())
    spans=evidence_keys(value)
    # Equal evidence alone is not proof of identical reasoning: normalized
    # proposition must also agree. Reward deduplicates atomic source spans.
    if any(c.label==hypothesis.label and ' '.join(c.proposition.casefold().split())==normalized
           and evidence_keys({'evidence_spans':c.evidence_spans})==spans for c in state.claims):
        raise ValueError('Duplicate grounded claim')
    span=value['evidence_spans'][0]
    from src.courtroom_rl.observation import frozen_text
    candidates=[c.claim_id for c in state.claims if c.label==hypothesis.label
        and c.author==role and c.kind==kind
        and float(frozen_text(c.proposition)@frozen_text(value['mechanism']))>=.9]
    claim=Claim(f'C{len(state.claims)+1}',role,hypothesis.label,value['mechanism'],
        {k:span[k] for k in ('source','quote','start','end')},created_step=state.decision_count,
        evidence_spans=value['evidence_spans'],hypothesis_id=hypothesis.id,kind=kind,
        similarity_review_candidates=candidates)
    state.claims.append(claim); hypothesis.claim_ids.append(claim.claim_id)
    return claim


def initialize(state,payload,budget):
    work=deepcopy(state)
    hypotheses=payload.get('hypotheses',[])
    if len(hypotheses)!=3 or len({h.get('label') for h in hypotheses})!=3:
        raise ValueError('Top3 must contain exactly three distinct labels')
    for rank,item in enumerate(hypotheses,1):
        if item['label'] not in FALLACIES or not 1<=len(item.get('claims',[]))<=budget.max_initial_claims_per_hypothesis:
            raise ValueError('Top3 requires valid labels with one or two claims')
        h=Hypothesis(f'H{rank}',item['label'],rank);work.hypotheses.append(h)
        for claim in item['claims']:
            append_claim(work,h,grounded(work,claim,True),'Prosecutor','SUPPORTING',budget)
    work.init_labels=[h.label for h in work.hypotheses]
    work.active_role='Defender';work.revision+=1
    for c in work.claims:
        work.seen_evidence_ids.extend(s['id'] for s in c.evidence_spans if s['id'] not in work.seen_evidence_ids)
    return work


def apply(state,action,payload,budget):
    """Return committed copy + selected target, or raise without mutating state."""
    work=deepcopy(state)
    if payload.get('no_op'):
        if action!='PROPOSE_ALTERNATIVE': raise ValueError('Unexpected no-op for eligible action')
        if payload.get('label') is not None or payload.get('evidence_ids'):
            raise ValueError('A no-op must not introduce a label or evidence')
        return work,None,True
    target=payload.get('claim_id') or payload.get('hypothesis_id')
    if action in ('CHALLENGE','SUPPORT','CONCEDE','REVISE') and target not in eligible(state,action):
        raise ValueError('LLM selected an ineligible target')
    if action=='CONCEDE':
        c=next(c for c in work.claims if c.claim_id==target);c.status='CONCEDED'
        # A concession does not declare the hypothesis correct.
        work.revision+=1
        return work,target,False
    value=grounded(work,payload,action in ('REVISE','PROPOSE_ALTERNATIVE'))
    unit=[state.active_role,action,target,sorted(evidence_keys(value)), ' '.join(value['mechanism'].casefold().split())]
    if unit in work.attempted_units:raise ValueError('Repeated action/target/evidence/reasoning')
    work.attempted_units.append(unit)
    if action in ('CHALLENGE','SUPPORT'):
        c=next(c for c in work.claims if c.claim_id==target)
        h=next(h for h in work.hypotheses if h.id==c.hypothesis_id)
        if action=='CHALLENGE':
            c.status='DISPUTED';c.challenge_count+=1;h.status='CHALLENGED'
            append_claim(work,h,value,state.active_role,'CONTRADICTING',budget)
        else:
            c.status='RESPONDED';c.response_count+=1;h.status='SUPPORTED'
            append_claim(work,h,value,state.active_role,'REBUTTAL',budget)
        value['label']=c.label
    else:
        label=value.get('label')
        if label not in FALLACIES:raise ValueError('Label outside eight classes')
        if action=='PROPOSE_ALTERNATIVE':
            if label in [h.label for h in work.hypotheses]:raise ValueError('Alternative label already in hypothesis pool')
            if len(work.hypotheses)>=budget.max_hypotheses:raise ValueError('Hypothesis capacity exhausted')
            h=Hypothesis(f'H{len(work.hypotheses)+1}',label,None);work.hypotheses.append(h);target=h.id
        elif action=='REVISE':
            old=next(h for h in work.hypotheses if h.id==target)
            old.visits+=1
            if label==old.label:h=old
            else:
                old.status='WEAKENED'
                h=next((h for h in work.hypotheses if h.label==label),None)
                if h is None:
                    if len(work.hypotheses)>=budget.max_hypotheses:raise ValueError('Hypothesis capacity exhausted')
                    h=Hypothesis(f'H{len(work.hypotheses)+1}',label,None);work.hypotheses.append(h)
        append_claim(work,h,value,state.active_role,'SUPPORTING',budget)
    for span in value['evidence_spans']:
        if span['id'] not in work.seen_evidence_ids:work.seen_evidence_ids.append(span['id'])
    work.revision+=1
    return work,target,False
