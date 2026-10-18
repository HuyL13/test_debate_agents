from copy import deepcopy
import re


def normalize(output,units):
    result=deepcopy(output);byid={u['id']:u for u in units};changes=[]
    for index,a in enumerate(result['arguments']):
        text=byid[a['conclusion']]['text'];lower=text.lower()
        value=None;rule=None
        envelope=byid[a['conclusion']].get('envelope',{}).get('text','').lower()
        denial=bool(re.search(r"does(?:n't| not) (?:mean|make|establish)|no reason|does not follow",lower))
        if lower.startswith('if ') and re.search(r'would not surprise|wouldn.t surprise',envelope):
            value='possible';rule='explicit hedged conditional in source envelope'
        elif re.search(r'\b(?:might|may|could|possibly|perhaps)\b|would not surprise|wouldn.t surprise',lower):
            value='possible';rule='explicit possibility cue in conclusion'
        elif re.search(r'\b(?:probably|likely)\b|seems reasonable',lower):
            value='probable';rule='explicit probability cue in conclusion'
        elif not denial and re.search(r'\bshould\b|\bought to\b|\bneed(?:s)? to\b|^please\b|^let.s\b|(?:we |i )?(?:can.t|cannot) allow',lower):
            value='normative';rule='explicit prescription cue in conclusion'
        elif not denial and re.search(r'\bmust\s+(?!be\b|have\b)',lower):
            value='normative';rule='deontic must with action predicate'
        if value is not None and value!=a['commitment']:
            changes.append({'argument_index':index,'field':'commitment','old':a['commitment'],'new':value,'anchor_unit_id':a['conclusion'],'rule':rule})
            a['commitment']=value
    return result,changes


def review_flags(output,units,include_testimony=False,include_critique=False):
    text=' '.join(u['text'] for u in units if u.get('source','comment')=='comment').lower()
    args=output['arguments'];ops={a['operator'] for a in args};flags=[]
    if include_critique and not any(a['stance']=='critiques' for a in args) and re.search(r'not (?:our|the|their|your) only (?:choices|options)|does(?:n.t| not) (?:mean|make|establish)|no reason|unsupported',text):
        flags.append('An explicit rejection cue occurs without a challenged inference. Inspect the rejected warrant and its actual conclusion anchors; do not turn a rebuttal into endorsement or force a critique when the rejection concerns something else.')
    if not args:flags.append('No grounded argument was extracted; inspect for implicit or intra-clause reasoning without inventing a conclusion.')
    if 'other' in ops:flags.append('A central warrant was left other; inspect whether its relation can be grounded more precisely.')
    cues=[
      ('alternatives',r'only (?:option|choice|thing|way)|either\b.{0,150}\bor\b|not (?:our|the|their|your) only (?:choices|options)'),
      ('priority_comparison',r'(?:more|less|as) important|worse problem|more (?:serious|severe|urgent|wide.spread)|not nearly as important'),
      ('generalization',r'\b(?:shows|means|proves)\b.{0,100}\b(?:all|every|entire)\b|\b(?:all|every)\b.{0,60}\b(?:bad|dishonest|corrupt)\b'),
      ('historical_practice',r'\btradition(?:al|ally)?\b|\bcenturies\b|\btime.tested\b'),
      ('natural_property',r'\bnatural(?:ly)?\b|human nature|built.in survival'),
      ('consensus',r'\bmajority\b|most people|many people (?:say|believe)|everyone (?:believes|wants)'),
    ]
    for operator,pattern in cues:
        if operator not in ops and re.search(pattern,text):
            flags.append('Source contains a possible '+operator+' cue not represented in the graph. It may be literal, reported, criticized or irrelevant: inspect, do not force this operator.')
    if include_testimony and 'testimony' not in ops and re.search(r'\bexperts?\b|\bspecialists?\b|according to|\bas\b.{0,90}\bsaid\b|\bto quote\b|\bwho (?:reads?|watches?)\b|\bwise to heed\b|\b(?:director|president|minister)\b.{0,100}\b(?:would appreciate|would support|endorses|recommends)\b',text):flags.append('A named-source/expertise/quotation/endorsement warrant may have been missed. Inspect whether the author actually relies on that source, rather than treating multiple experts as mere popularity or using generic factual evidence. Testimony/status support can justify an action or evaluation as well as a factual claim; a quoted statement is not required if the attributed endorsement is actually used. Mentioning a politician/organization alone is not enough; do not force testimony.')
    if 'consensus' in ops and not re.search(r'believ|think|say|opinion|popular|majority|most|many|agree|vote|will of|participat|everyone|everybody',text):flags.append('A consensus warrant was extracted without an apparent belief/popularity/group-choice basis. Check that it is not merely a generic claim ABOUT people or a title topic; remove/correct unsupported warrants.')
    if any(u.get('source')=='parent_comment' for u in units) and re.search(r'you are right|makes (?:a lot of )?sense|i agree|exactly',text) and not any(any(next(u for u in units if u['id']==i).get('source')=='parent_comment' for i in a['premises']+a['chain']) for a in args):flags.append('The comment explicitly agrees with parent context but none of the adopted reasoning was represented. Check whether qualified parent links support the comment; do not inherit stronger certainty than the comment expresses.')
    if len(re.findall(r'will lead|would lead',text))>=2 and not any(len(a['chain'])>=2 for a in args):flags.append('Repeated projected-step cues exist but no grounded event chain was retained; inspect actual event clauses.')
    if 'generalization' in ops:flags.append('Check each generalization: its premises must anchor the observed sample/property, not merely the previous conclusion; verify a real scope expansion rather than generic concern.')
    return flags
