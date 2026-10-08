import re

from src.labels import FALLACIES
from src.discourse_classification.graph import CAUSAL

# These cues retrieve possibilities only; ownership and inferential defects are verified later.
CUES = {
    'Appeal to Authority': r'\b(according to|experts?|authorit\w*|professors?|scientists?|study|studies|renowned|president|government|says?|claims?|listen to)\b',
    'Appeal to Majority': r'\b(everyone|most people|majority|popular|widely|many people|common belief|everybody)\b',
    'Appeal to Nature': r'\b(natur\w*|unnatural\w*|biolog\w*|born|instinct\w*)\b',
    'Appeal to Tradition': r'\b(tradition\w*|generations?|histor\w*|always|long-standing|used to|centuries|ancestors?|custom\w*|precedent)\b',
    'Appeal to Worse Problems': r'\b(worse|bigger|more urgent|more important|trivial|focus|priorit\w*|instead|other problems?)\b',
    'False Dilemma': r'\b(either|or|only|no other|two (?:choices|options|solutions|situations)|other options)\b',
    'Hasty Generalization': r'\b(all|everyone|always|never|forever|nothing|governments|in general|must mean|this incident|these people)\b',
    'Slippery Slope': r'\b(if|then|lead\w*|result\w*|eventually|next|will|end up|before long)\b',
}
MOTIFS = {
    'False Dilemma': {'ALTERNATIVE'}, 'Appeal to Worse Problems': {'COMPARISON', 'CONTRAST'},
    'Hasty Generalization': {'GENERALIZATION'},
    'Slippery Slope': {'CAUSE', 'CONSEQUENCE', 'CONDITION', 'SEQUENCE'},
    **{label: {'SUPPORT', 'JUSTIFICATION'} for label in FALLACIES[:4]},
}
MECHANISMS = {
    'Appeal to Authority': 'A source endorsement or authority status is used materially to justify a claim.',
    'Appeal to Majority': 'Popularity or a group belief/behavior is used to justify truth, value, or acceptance.',
    'Appeal to Nature': 'Naturalness or unnaturalness is used to infer value, correctness, preference, or inevitability.',
    'Appeal to Tradition': 'Historical persistence, inherited practice, or precedent is used to justify correctness or continuation.',
    'Appeal to Worse Problems': 'A more serious issue is used to dismiss, downplay, or redirect attention from the focal concern.',
    'False Dilemma': 'A restricted set of alternatives is presented as exhaustive and matters to the argument.',
    'Hasty Generalization': 'A broad conclusion is justified by limited evidence, including evidence implicit in context.',
    'Slippery Slope': 'An initial action is linked to an escalating/extreme consequence as a warning; the chain may be compressed to one step.',
}
DEFECTS = {
    'Appeal to Authority': 'Authority is treated as sufficient proof beyond the support actually provided.',
    'Appeal to Majority': 'Popularity substitutes for evidence of correctness or value.',
    'Appeal to Nature': 'Natural status alone substitutes for the relevant evaluative justification.',
    'Appeal to Tradition': 'Longevity or precedent substitutes for relevant justification.',
    'Appeal to Worse Problems': 'Relative severity substitutes for engagement with the focal concern, rather than a substantiated resource tradeoff.',
    'False Dilemma': 'The restricted choice space is unjustified: plausible alternatives are excluded.',
    'Hasty Generalization': 'The evidence is insufficient or unrepresentative for the conclusion.',
    'Slippery Slope': 'The transition to the extreme consequence is insufficiently supported.',
}


BRIDGES = {
    'Hasty Generalization': 'SAMPLE_TO_POPULATION', 'Slippery Slope': 'ACTION_TO_CONSEQUENCE',
    'False Dilemma': 'RESTRICTED_CHOICE', 'Appeal to Worse Problems': 'ISSUE_TO_DEPRIORITIZATION',
    **{label: 'SOURCE_TO_CLAIM' for label in FALLACIES[:4]},
}
SPECIFIC = r'\b(?:one|few|small|this|these|some|my)\s+(?:incident|case|example|sample|experience|people|government|official)s?\b'
BROAD = r'\b(?:all|everyone|always|never|most|generally|every|people|governments)\b'
EVALUATIVE = r'\b(?:good|bad|right|wrong|correct|true|better|should|must|keep|continue|accept|follow|trust|believe|justif\w*)\b'
EXTREME = r'\b(?:silenc\w*|collaps\w*|execut\w*|destroy\w*|catastroph\w*|extinct\w*|totalitarian\w*|imprison\w*|jail|all\s+power)\b'
ESCALATION = r'\b(?:more\s+and\s+more|eventually|until|what\s+comes\s+next|after\s+that)\b'


def retrieve(graph, max_per_label=3):
    candidates = []
    nodes = graph['propositions']
    by_id = {n['id']: n for n in nodes}
    for label in FALLACIES:
        options = []
        for r in graph['relations']:
            args = [by_id[r['arg1']], by_id[r['arg2']]]
            combined = ' '.join(n['text'] for n in args)
            supported = r['type'] in MOTIFS[label]
            if label in FALLACIES[:4]:
                supported &= bool(re.search(CUES[label], combined, re.I) and re.search(EVALUATIVE, combined, re.I))
            if label == 'Hasty Generalization':
                supported &= bool(re.search(SPECIFIC, combined, re.I) and re.search(BROAD, combined, re.I))
            if label == 'Appeal to Worse Problems':
                supported &= bool(re.search(r'\b(?:worse|bigger|greater|more\s+(?:urgent|important|serious)|less\s+important|not\s+in\s+the\s+top)\b', combined, re.I))
            if supported:
                ids = [n['id'] for n in args]
                relations = [r['id']]
                if label == 'Slippery Slope':
                    # Connected paths/questions are one argument, rather than isolated steps.
                    for _ in range(3):
                        for edge in graph['relations']:
                            if edge['type'] in MOTIFS[label] and {edge['arg1'], edge['arg2']} & set(ids):
                                ids = list(dict.fromkeys(ids + [edge['arg1'], edge['arg2']]))
                                relations = list(dict.fromkeys(relations + [edge['id']]))
                    # Resolve only the local structural anchor for anaphoric starts, not its semantics.
                    first = min(nodes.index(by_id[nid]) for nid in ids)
                    if first and re.search(r'\b(?:it|this|that)\b', by_id[ids[0]]['text'], re.I):
                        ids.insert(0, nodes[first-1]['id'])
                options.append(('explicit' if r['source'] == 'explicit' else 'partial', ids, relations))
        for n in nodes:
            text = n['text']
            anchored = False
            if label == 'Hasty Generalization':
                anchored = bool(re.search(SPECIFIC, text, re.I) and re.search(BROAD, text, re.I)
                    and re.search(r'\b(?:prove\w*|mean\w*|show\w*|therefore|so|because)\b', text, re.I))
            elif label == 'Slippery Slope':
                anchored = bool(re.search(CAUSAL, text, re.I) and re.search(EXTREME + '|' + ESCALATION, text, re.I))
                if re.match(r'(?:(?:though|but|however)\s+)?(?:it|this|that)\b', text, re.I) and any(
                        r['arg2'] == n['id'] and r['type'] in MOTIFS[label] for r in graph['relations']):
                    anchored = False  # The connected candidate already contains its antecedent.
            elif label in FALLACIES[:4]:
                anchored = bool(re.search(CUES[label], text, re.I) and re.search(EVALUATIVE, text, re.I)
                    and re.search(r'\b(?:because|therefore|so|since|must|should|are|is|has|have|says?|according to)\b', text, re.I))
            if anchored:
                ids = [n['id']]
                if label == 'Appeal to Tradition':
                    index = nodes.index(n)
                    history = [p['id'] for p in nodes[max(0, index-2):index]
                               if re.search(CUES[label] + r'|\bas old as time\b', p['text'], re.I)]
                    ids = history + ids
                options.append(('construction', ids, []))
        seen = set()
        for mode, ids, relations in options:
            key = tuple(sorted(ids))
            if key in seen:
                continue
            seen.add(key)
            indices = [i for i, n in enumerate(nodes) if n['id'] in ids]
            context = [n['id'] for i, n in enumerate(nodes) if min(abs(i-j) for j in indices) <= 2 and n['id'] not in ids]
            candidates.append({'candidate_id': f'C{len(candidates)+1}', 'label': label,
                'retrieval_mode': mode, 'nodes': ids, 'relations': relations, 'context_nodes': context,
                'bridge_type': BRIDGES[label],
                'anchor': 'intra-clause premise/conclusion construction' if mode == 'construction' else 'connected discourse motif'})
            if len(seen) >= max_per_label:
                break
    return candidates
