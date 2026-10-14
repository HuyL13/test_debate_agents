"""Courtroom source namespaces/offsets over the existing evidence resolver."""
import re

from src.evidence import target_passages, resolve_evidence


def passages_for(case_input, target_only=False):
    passages = []
    sources = [('comment','T')] if target_only else [('comment','T'),('parent_comment','P'),('title','H')]
    for source,prefix in sources:
        text = getattr(case_input,source)
        previous, index = 0, 0
        boundaries = [m.end() for m in re.finditer(r'''[.!?](?:["”’']+)?(?=\s|$)|\n+''',text)]
        for boundary in boundaries+[len(text)]:
            raw = text[previous:boundary]
            start = previous+len(raw)-len(raw.lstrip())
            end = boundary-(len(raw)-len(raw.rstrip()))
            previous = boundary
            if start >= end:
                continue
            sentence = text[start:end]
            # Preserve ordinary complete sentences. Bound exceptionally long
            # unpunctuated spans with the repository's existing 30-word splitter.
            chunks = target_passages(sentence) if len(sentence.split()) > 120 else [
                {'start':0,'end':len(sentence),'text':sentence}]
            for chunk in chunks:
                index += 1
                passages.append({'id':f'{prefix}{index}','source':source,
                    'start':start+chunk['start'],'end':start+chunk['end'],'text':chunk['text']})
    if target_only and not passages:
        raise ValueError('Cannot ground an empty target comment')
    return passages


def evidence_schema(passages, allow_empty=False, max_items=3):
    return {'type':'array','items':{'type':'string','enum':[p['id'] for p in passages]},
            'minItems':0 if allow_empty else 1,'maxItems':max_items}


def resolve_references(output, passages, allow_empty=False, max_items=3):
    ids = output.get('evidence_ids')
    if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids):
        raise ValueError('evidence_ids must be a list of supplied IDs')
    if len(ids) > max_items or len(set(ids)) != len(ids) or (not ids and not allow_empty):
        raise ValueError('Select distinct evidence IDs within the permitted count')
    resolved = resolve_evidence({'evidence_ids':ids},passages)
    lookup = {p['id']:p for p in passages}
    spans = [{'id':i,'source':lookup[i]['source'],'start':lookup[i]['start'],'end':lookup[i]['end'],
              'quote':quote} for i,quote in zip(ids,resolved['evidence_spans'])]
    return {**output,'evidence_spans':spans,
            'supported_quote':spans[0]['quote'] if spans else '',
            'source':spans[0]['source'] if spans else 'comment'}
