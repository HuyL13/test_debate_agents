"""Dependency-licensed alternatives with source-owned whitespace token spans.

Frames describe wording and uncertainty, never a fallacy or author endorsement.
Token bounds are half-open, as in ontology_v2.proposition_span.
"""
import re
from syntax_v2 import _nlp, _LOCK

VERSION='choice-syntax-r1'
_CLOSURE=re.compile(r'\beither\b|\bonly\s+(?:two\s+)?(?:choices|options|alternatives)\b|\bno\s+other\s+(?:choice|option|alternative)s?\b|\bfew\s+choices\b|\bor\s+nothing\b|\bblack\s+and\s+white\b',re.I)
_EXPANSION=re.compile(r'\bmore\s+(?:options|choices|alternatives)\s+than\b',re.I)

def _anchor(unit,a,b):
    tokens=unit['tokens']; origin=unit['start']
    selected=[i for i,t in enumerate(tokens) if t['end']>origin+a and t['start']<origin+b]
    if not selected:return None
    first,last=selected[0],selected[-1]+1
    start=tokens[first]['start']-origin; end=tokens[last-1]['end']-origin
    return dict(unit=unit['id'],first=first,last=last,text=unit['text'][start:end])

def _tokens_span(unit,tokens):
    tokens=[t for t in tokens if not t.is_punct and not t.is_space and t.lower_!='either']
    if not tokens:return None
    return _anchor(unit,min(t.idx for t in tokens),max(t.idx+len(t) for t in tokens))

def choice_frames(sample,units):
    """Return deterministic frames; no mutation of sample or source units.

    relation is coordinated_alternatives or proposed_additional_option.
    Closure cues may be rejected: consumers must inspect rejection_cues.
    Cross-unit cue attachment is limited to an immediately following same-source
    explicit restriction/expansion. Additional proposals remain separate frames.
    """
    result=[]; previous=None
    for unit in units:
        text=unit['text']
        with _LOCK: doc=_nlp()(text)
        closure=[_anchor(unit,m.start(),m.end()) for m in _CLOSURE.finditer(text)]
        expansion=[_anchor(unit,m.start(),m.end()) for m in _EXPANSION.finditer(text)]
        neg=[t for t in doc if t.dep_=='neg']
        rejection=[]
        # A negated governing predicate scopes a restriction cue; include the
        # entire clause so the anchor cannot lose its negation or modal.
        if closure and neg:
            for n in neg:
                governing=set(t.i for t in n.head.subtree)
                if any(t.i in governing and any(t.idx < m.end() and t.idx+len(t)>m.start() for m in _CLOSURE.finditer(text)) for t in doc):
                    rejection=[_anchor(unit,0,len(text))];break
        rejection+=expansion
        frames=[]
        for cc in doc:
            if cc.lower_!='or' or cc.dep_!='cc':continue
            left=cc.head
            right=next((c for c in left.children if c.dep_=='conj' and c.i>cc.i),None)
            if right is None:continue
            left_tokens=[t for t in left.subtree if t.i<cc.i and t.lower_!='either']
            # Existential "a way through X or doing Y" is often attached by
            # the parser at the clause root: recover X from its nominal head.
            if any(c.dep_=='expl' for c in left.children):
                nominals=[t for t in left_tokens if t.dep_=='pobj']
                if nominals:left_tokens=list(nominals[-1].subtree)
            right_tokens=[t for t in right.subtree if t.i>cc.i]
            options=[_tokens_span(unit,left_tokens),_tokens_span(unit,right_tokens)]
            if not all(options):continue
            uncertainty=[]
            if any(t.lower_ in ['this','that','nothing'] for t in [left,right]):uncertainty.append('deictic_or_unspecified_option')
            if text.rstrip().endswith('?'):uncertainty.append('question')
            if any(t.lower_ in ['might','may','could','maybe','perhaps'] for t in doc):uncertainty.append('tentative')
            frames.append(dict(unit=unit['id'],source=unit['source'],scope=_anchor(unit,0,len(text)),options=options,closure_cues=closure.copy(),rejection_cues=rejection.copy(),uncertainty=uncertainty,relation='coordinated_alternatives'))
        # A tentative gerund proposal following alternatives contributes its own
        # option, without asserting a closed or author-endorsed option set.
        roots=[t for t in doc if t.dep_=='ROOT']
        if not frames and previous and previous['source']==unit['source'] and roots and roots[0].tag_=='VBG' and any(t.lower_ in ['maybe','perhaps'] for t in doc):
            proposal=_tokens_span(unit,[t for t in roots[0].subtree if t.lower_ not in ['maybe','perhaps']])
            if proposal:frames.append(dict(unit=unit['id'],source=unit['source'],scope=_anchor(unit,0,len(text)),options=[proposal],closure_cues=[],rejection_cues=[],uncertainty=['tentative','additional_option_link_uncertain'],relation='proposed_additional_option'))
        if not frames and previous and previous['source']==unit['source'] and previous['unit']==unit['id']-1:
            previous['closure_cues'].extend(closure)
            previous['rejection_cues'].extend(expansion)
        for frame in frames:
            frame['id']='choice:'+str(frame['unit'])+':'+str(len([f for f in result if f['unit']==frame['unit']]))
            result.append(frame)
        if frames:previous=frames[-1]
    return result
