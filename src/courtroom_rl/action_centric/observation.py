"""CREW action rows: six public past-only features, validity flags + globals."""
import numpy as np
from src.courtroom_rl.action_centric.state import ROLE_ACTIONS
from src.courtroom_rl.action_centric.ledger import eligible

GLOBAL_DIM=8
OBS_DIMS={r:len(actions)*7+GLOBAL_DIM for r,actions in ROLE_ACTIONS.items()}


def encode(env):
    s,b=env.state,env.budget
    rows=[];legal=env.legal_actions()
    disputes=[c for c in s.claims if c.status=='DISPUTED']
    count=max(1,len(s.claims));unseen=max(0,8-len(s.hypotheses))/8
    remaining=max(0.,1-(s.input_tokens+s.output_tokens)/b.max_tokens)
    for action in ROLE_ACTIONS[s.active_role]:
        candidates=eligible(s,action)
        opportunity=len(candidates)/max(b.max_claims,b.max_hypotheses)
        gap=len(disputes)/count
        novelty=float(bool(candidates))
        if action=='REVISE':opportunity=sum(h.status in ('CHALLENGED','WEAKENED') for h in s.hypotheses)/b.max_hypotheses
        if action=='PROPOSE_ALTERNATIVE':opportunity=unseen;novelty=unseen
        if action=='CONCEDE':gap=len([c for c in s.claims if c.status=='OPEN'])/count;novelty=0.
        if action=='REST':opportunity=1.-len(disputes)/count;novelty=0.
        if action=='REQUEST_SUPPORT':opportunity=len(eligible(s,'SUPPORT'))/b.max_claims
        if action=='REQUEST_REBUTTAL':opportunity=len(eligible(s,'CHALLENGE'))/b.max_claims
        if action=='VERDICT':opportunity=1.-len(disputes)/count;novelty=0.;gap=len(disputes)/count
        relevance=opportunity
        candidate_action={'REQUEST_SUPPORT':'SUPPORT','REQUEST_REBUTTAL':'CHALLENGE'}.get(action,action)
        relevance_candidates=eligible(s,candidate_action) if env.semantic_observation else candidates
        if env.semantic_observation and relevance_candidates:
            texts=[c.proposition for c in s.claims if (c.hypothesis_id if action=='REVISE' else c.claim_id) in relevance_candidates]
            if texts:
                if env.text_encoder is None:
                    raise ValueError('Semantic observations require a text encoder')
                source='\n'.join([s.case_input.title,s.case_input.parent_comment,s.case_input.comment])
                vectors=env.text_encoder.encode([source]+texts)
                relevance=max(0.,float(np.max(vectors[1:]@vectors[0])))
        stats=s.action_stats.get(s.active_role+'.'+action,{})
        impact=stats.get('impact',.5);n=stats.get('n',0)
        observed_cost=(stats.get('tokens',0)/max(1,n))/b.max_tokens
        affordable=max(0.,remaining-observed_cost) if action in legal else 0.
        rows.extend([relevance,opportunity,gap,novelty,impact,affordable,float(n>0)])
    rows.extend([s.decision_count/b.max_decisions,remaining,max(0.,1-s.calls/b.max_calls),
        len(s.hypotheses)/b.max_hypotheses,len(s.claims)/b.max_claims,
        float(s.pending_request is not None),float(s.forced_verdict),
        float(all(s.role_status.values()))])
    result=np.clip(np.array(rows,dtype=np.float32),0,1)
    assert result.shape==(OBS_DIMS[s.active_role],)
    return result
