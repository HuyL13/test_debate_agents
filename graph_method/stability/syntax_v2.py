"""Independent dependency frames; these are typed source cues, not truth checks."""
from copy import deepcopy
from functools import lru_cache
import threading

MODEL='en_core_web_sm'
VERSION='syntax-frames-r1'
_LOCK=threading.Lock()
NORM_MODALS={'should','must','ought'}
FUTURE_MODALS={'will','would','may','might','could'}
CAUSAL_PREDICATES={'lead','cause','trigger','result','produce','precipitate'}
EPISTEMIC_PREDICATES={'trust','believe','think','know','doubt','suspect','assume','conclude'}
LOGICAL_PREDICATES={'justify','imply','entail','prove','mean'}
REPORTING_PREDICATES={'say','report','tell','claim','argue','announce','write','hear','talk'}
FUNCTIONAL_ACTIONS={'be','have','do','need','want','allow','permit','mean','justify','imply','entail','prove'}
META_NOUNS={'line','question','difficulty','dilemma','sword','spot'}
EVALUATIVE_ADJECTIVES={'good','bad','great','fine','right','wrong','important','tragic','disheartening','difficult','hard','tough'}

@lru_cache(maxsize=1)
def _nlp():
    try:import spacy
    except ImportError as exc:raise RuntimeError('Syntax mode requires .venv-syntax/Scripts/python.exe and the pinned en_core_web_sm model') from exc
    return spacy.load(MODEL,disable=['ner'])


def _token(t):return dict(text=t.text,lemma=t.lemma_.lower(),pos=t.pos_,dep=t.dep_,start=t.idx,end=t.idx+len(t))


def _span(text,tokens):
    tokens=[t for t in tokens if not t.is_space and not t.is_punct]
    if not tokens:return None
    start=min(t.idx for t in tokens);end=max(t.idx+len(t) for t in tokens)
    return dict(start=start,end=end,text=text[start:end])


def _profile(doc):
    text=doc.text
    roots=[t for t in doc if t.dep_=='ROOT']
    if not roots:return dict(content_kind='unknown',initial_eligible=False,outcome_eligible=False,forecast=False,action_predicates=[],condition_spans=[],effect_span=None,effect_predicate=None,modality='unspecified',root=None,predicate=None,reasons=['no syntactic root'])
    root=roots[0];predicate=root
    if root.lemma_=='be':predicate=next((c for c in root.children if c.dep_ in ['attr','acomp','oprd']),root)
    root_modals={c.lemma_.lower() for c in root.children if c.dep_ in ['aux','auxpass']}
    future=bool(root_modals&FUTURE_MODALS)
    conditional_heads=[c for c in root.children if c.dep_=='advcl' and any(t.dep_=='mark' and t.lemma_.lower() in ['if','unless','when'] for t in c.children)]
    conditions=[_span(text,list(t.subtree)) for t in conditional_heads]
    conditions=[s for s in conditions if s]
    direct_condition=any(c.dep_=='mark' and c.lemma_.lower() in ['if','unless'] for c in root.children)
    pending=[predicate];action_tokens=[];seen=set()
    while pending:
        t=pending.pop()
        if t.i in seen:continue
        seen.add(t.i)
        if t.pos_=='VERB' and t.lemma_.lower() not in FUNCTIONAL_ACTIONS and t.dep_!='amod':action_tokens.append(t)
        pending.extend(c for c in t.children if c.dep_ in ['xcomp','ccomp'])
    actions=sorted({t.lemma_.lower() for t in action_tokens})
    norm=bool(root_modals&NORM_MODALS) or root.lemma_=='need' and any(c.dep_=='xcomp' for c in root.children)
    imperative=root.pos_=='VERB' and root.tag_=='VB' and not any(c.dep_ in ['nsubj','nsubjpass','csubj'] for c in root.children) and root.i==0
    question=text.rstrip().endswith('?')
    main_lemma=predicate.lemma_.lower();root_lemma=root.lemma_.lower()
    meta=root_lemma=='be' and (main_lemma in META_NOUNS or main_lemma in ['difficult','hard','tough']) and not future
    epistemic=root_lemma in EPISTEMIC_PREDICATES and not future and not direct_condition
    logical=root_lemma in LOGICAL_PREDICATES
    if meta:kind='metacomment'
    elif norm or imperative:kind='normative_action' if actions else 'normative_evaluation'
    elif epistemic:kind='epistemic_evaluation'
    elif logical:kind='logical_evaluation'
    elif predicate.pos_=='ADJ' and not future:kind='evaluation'
    elif root_lemma in REPORTING_PREDICATES and not future:kind='reported_content'
    elif root.pos_=='VERB' or future and predicate.pos_=='ADJ' and main_lemma not in EVALUATIVE_ADJECTIVES:kind='event_description'
    else:kind='unknown'
    initial=kind=='event_description' or kind=='normative_action'
    # A permission question with an actual action complement is a scenario,
    # while a broad metacomment about what is allowed is not a concrete event.
    if root_lemma in ['allow','permit'] and not actions:initial=False
    outcome=kind=='event_description'
    causal=root_lemma in CAUSAL_PREDICATES
    subjects=[c for c in root.children if c.dep_ in ['nsubj','nsubjpass','csubj']]
    deictic=any(c.lemma_.lower() in ['this','that','it'] for c in subjects)
    nominal_action=any(c.pos_=='VERB' for c in subjects)
    past=root.tag_=='VBD' and not future
    forecast=outcome and (future or bool(conditions) or causal and (deictic or nominal_action) and not past)
    modality='possible' if root_modals&{'may','might','could'} else 'probable' if any(t.lemma_.lower() in ['likely','probably'] for t in doc) else 'unspecified' if norm or imperative or question or direct_condition or epistemic else 'certain'
    effect=None;effect_predicate=None
    if causal:
        effect_head=None
        for child in root.children:
            if child.dep_=='prep' and child.lemma_.lower() in ['to','in','into']:
                effect_head=next((c for c in child.children if c.dep_ in ['pobj','pcomp']),None)
                if effect_head is not None:break
        if effect_head is None:effect_head=next((c for c in root.children if c.dep_ in ['dobj','obj','ccomp']),None)
        if effect_head is not None:
            effect=_span(text,list(effect_head.subtree))
            effect_verb=next((t for t in effect_head.subtree if t.pos_=='VERB' and t.dep_ in ['acl','ROOT','ccomp','pcomp'] and t.lemma_.lower() not in FUNCTIONAL_ACTIONS),None)
            effect_predicate=effect_verb.lemma_.lower() if effect_verb is not None else effect_head.lemma_.lower()
    if effect is None and outcome:
        excluded={t.i for head in conditional_heads for t in head.subtree}
        effect=_span(text,[t for t in root.subtree if t.i not in excluded])
        effect_predicate=root_lemma
    reasons=[]
    if meta:reasons.append('copular discourse description is not an initiating event')
    if norm or imperative:reasons.append('normative action/requirement is not a predicted outcome')
    if epistemic:reasons.append('epistemic assessment is not a predicted change in the world')
    if kind=='evaluation':reasons.append('present evaluation is not a projected event')
    return dict(version=VERSION,parser=MODEL,root=_token(root),predicate=_token(predicate),main_modals=sorted(root_modals),content_kind=kind,initial_eligible=initial,outcome_eligible=outcome,forecast=forecast,action_predicates=actions,condition_spans=conditions,effect_span=effect,effect_predicate=effect_predicate,modality=modality,question=question,negated=any(c.dep_=='neg' for c in root.children),deictic_cause=deictic,reasons=reasons)


@lru_cache(maxsize=8192)
def _cached(text):
    with _LOCK:doc=_nlp()(text)
    return _profile(doc)


def analyse_text(text):
    if not isinstance(text,str):raise ValueError('source text required')
    return deepcopy(_cached(text))
