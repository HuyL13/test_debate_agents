"""Fixed public semantic observation contract; encoders never receive rewards or gold."""
import json
import numpy as np
from src.labels import FALLACIES
from src.courtroom_rl.action_centric.state import ROLE_ACTIONS
from src.courtroom_rl.action_centric.embeddings import FixtureEncoder
from .executor import dialogue_view
TEXT_DIM=768
MAX_OBJECTS=16
MAX_HISTORY=10
OBJECT_FEATURE_DIM=34
GLOBAL_DIM=12
OBS_DIMS={'source':[768],'objects':[16,768],'object_features':[16,34],'object_mask':[16],'ids':16,'history':[10,768],'history_mask':[10],'global':[12]}
STATUSES=('OPEN','DISPUTED','RESPONDED','CONCEDED','UNRESOLVED','CLOSED','ACTIVE','CHALLENGED','SUPPORTED','WEAKENED','REJECTED','RESOLVED')
ROLES=('Prosecutor','Defender','Judge')
KINDS=('SUPPORTING','CONTRADICTING','REBUTTAL')


def encode(env):
    s,b=env.state,env.budget
    encoder=env.text_encoder
    if encoder is None:raise ValueError('V4 requires an explicit frozen text encoder')
    objects=list(s.hypotheses)+list(s.claims)
    if len(objects)>MAX_OBJECTS:raise ValueError('Observation object capacity exceeded')
    history=dialogue_view(s)['argument_events'][-MAX_HISTORY:]
    source='\n'.join((s.case_input.title,s.case_input.parent_comment,s.case_input.comment))
    texts=[source]
    for o in objects:
        if hasattr(o,'id'):
            claims=[c.proposition for c in s.claims if c.hypothesis_id==o.id]
            texts.append(o.label+'\n'+'\n'.join(claims))
        else:texts.append(o.label+'\n'+o.proposition+'\n'+'\n'.join(x['quote'] for x in o.evidence_spans))
    texts += [json.dumps(e,sort_keys=True,ensure_ascii=False) for e in history]
    vectors=np.asarray(encoder.encode(texts),dtype=np.float32)
    if isinstance(encoder,FixtureEncoder) and vectors.shape==(len(texts),128):
        vectors=np.pad(vectors,((0,0),(0,TEXT_DIM-128)))
    if vectors.shape!=(len(texts),TEXT_DIM) or not np.isfinite(vectors).all():raise ValueError('Encoder must return finite 768 dimensional embeddings')
    result={'source':vectors[0].copy(),'objects':np.zeros((MAX_OBJECTS,TEXT_DIM),np.float32),
        'object_features':np.zeros((MAX_OBJECTS,OBJECT_FEATURE_DIM),np.float32),
        'object_mask':np.zeros(MAX_OBJECTS,bool),'ids':[None]*MAX_OBJECTS,
        'history':np.zeros((MAX_HISTORY,TEXT_DIM),np.float32),'history_mask':np.zeros(MAX_HISTORY,bool)}
    for i,o in enumerate(objects):
        hyp=hasattr(o,'id');f=result['object_features'][i]
        result['objects'][i]=vectors[i+1];result['object_mask'][i]=True
        result['ids'][i]=o.id if hyp else o.claim_id
        f[FALLACIES.index(o.label)]=1
        author=next((c.author for c in s.claims if c.hypothesis_id==o.id),'Prosecutor') if hyp else o.author
        f[8+ROLES.index(author)]=1
        f[11+STATUSES.index(o.status)]=1
        if not hyp:f[23+KINDS.index(o.kind)]=1
        f[26+int(not hyp)]=1
        if hyp:stats=[o.visits/2,len(o.claim_ids)/b.max_claims,(o.initial_rank or 0)/3,0,0,0]
        else:stats=[o.challenge_count,o.response_count,o.created_step/b.max_decisions,len(o.evidence_spans)/3,len(o.supporting_ids)/b.max_claims,len(o.attacks_ids)/b.max_claims]
        f[28:]=np.clip(stats,0,1)
    if history:
        result['history'][:len(history)]=vectors[1+len(objects):]
        result['history_mask'][:len(history)]=True
    result['global']=np.clip(np.asarray([s.decision_count/b.max_decisions,
        1-(s.input_tokens+s.output_tokens)/b.max_tokens,1-s.calls/b.max_calls,
        len(s.hypotheses)/b.max_hypotheses,len(s.claims)/b.max_claims,
        float(s.pending_request is not None),float(s.forced_verdict),float(all(s.role_status.values())),
        float(s.role_status['Prosecutor']),float(s.role_status['Defender']),
        float(bool(s.pending_request) and s.pending_request['role']=='Prosecutor'),
        float(bool(s.pending_request) and s.pending_request['role']=='Defender')],dtype=np.float32),0,1)
    return result
