"""Frozen signed word/bigram hashing; deterministic, compact CPU text features."""
import hashlib
import re

import numpy as np

from src.courtroom_rl.schemas import ACTIONS, ROLES
from src.labels import FALLACIES


TEXT_DIM = 128
CLAIM_DIM = TEXT_DIM+8+3+6+4
OBS_DIM = TEXT_DIM+3+8+8+11+12+3*CLAIM_DIM
STATUSES = ('OPEN', 'DISPUTED', 'RESPONDED', 'CONCEDED', 'UNRESOLVED', 'CLOSED')


def frozen_text(text):
    words = re.findall(r"[\w']+", text.casefold())
    features = np.zeros(TEXT_DIM, dtype=np.float32)
    for token in words+[' '.join(pair) for pair in zip(words, words[1:])]:
        value = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), 'little')
        features[value % TEXT_DIM] += 1. if value & 256 else -1.
    norm = np.linalg.norm(features)
    return features / max(norm, 1.)


def one_hot(value, choices):
    return [float(value == x) for x in choices]


def encode(env):
    s, b = env.state, env.budget
    obs = list(frozen_text('\n'.join(s.case_input.as_dict().values())))
    obs += one_hot(s.active_role, ROLES)+one_hot(s.charge_label, FALLACIES)
    obs += [float(x in s.tested_labels) for x in FALLACIES]
    obs += [sum(h[1] == a for h in s.action_history)/b.max_decisions for a in ACTIONS]
    obs += [s.decision_count/b.max_decisions, max(0., 1-s.calls/b.max_calls),
            max(0., 1-(s.input_tokens+s.output_tokens)/b.max_tokens),
            float(s.defense_exposed), float(s.revised), float(s.alternative_proposed),
            float(s.role_status['Prosecutor']), float(s.role_status['Defender']),
            float(s.pending_request is not None), float(s.pending_request is not None and s.pending_request[0] == 'Prosecutor'),
            float(s.pending_request is not None and s.pending_request[0] == 'Defender'), float(s.forced_verdict)]
    for index in range(3):
        if index >= len(s.claims):
            obs += [0.]*CLAIM_DIM
            continue
        c = s.claims[index]
        related = [event['action']+' '+event.get('payload',{}).get('mechanism','')
                   for event in s.argument_events if event.get('target') == c.claim_id]
        quotes = ' '.join(span['quote'] for span in c.evidence_spans) if c.evidence_spans else c.source_span['quote']
        obs += list(frozen_text(c.proposition+' '+quotes+' '+' '.join(related)))
        obs += one_hot(c.label, FALLACIES)+one_hot(c.author, ROLES)+one_hot(c.status, STATUSES)
        obs += [float(c.challenge_count), float(c.response_count),
                (s.decision_count-c.created_step)/b.max_decisions,
                float(s.pending_request is not None and s.pending_request[1] == c.claim_id)]
    result = np.asarray(obs, dtype=np.float32)
    assert result.shape == (OBS_DIM,)
    return result
