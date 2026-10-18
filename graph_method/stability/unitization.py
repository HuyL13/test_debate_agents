import re

BOUNDARY=re.compile(
    r'(?<=[.!?])\s+|(?<=[.!?]["\'])\s+|;\s*'
    r'|,\s+(?=(?:but|so|therefore|because|since|yet|whereas|although|which\s+(?:will|would))\b)'
    r'|\s+(?=(?:because|therefore|hence|thus)\b)'
    r'|\s+(?=(?:shows|proves|suggests|implies|means)\s+(?:that\b|it\b|they\b|we\b|the\b))'
    r'|,\s+(?=which\s+(?:will|would)\s+lead\b)',re.I)


def split_units_v4(source):
    result=[]
    for field in ['comment','title','parent_comment']:
        text=source.get(field,'');last=0
        boundaries=[]
        for match in BOUNDARY.finditer(text):
            boundaries.append((last,match.start()));last=match.end()
        boundaries.append((last,len(text)))
        for a,b in boundaries:
            fragment=text[a:b];start=a+len(fragment)-len(fragment.lstrip());end=b-(len(fragment)-len(fragment.rstrip()))
            if start<end:result.append({'id':len(result),'source':field,'start':start,'end':end,'text':text[start:end]})
    return result


def split_units_v5(source):
    initial=split_units_v4(source);result=[]
    for unit in initial:
        if result and result[-1]['source']==unit['source']:
            previous=result[-1]
            dangling_aux=re.search(r'\b(?:can|could|may|might|will|would|must|should|is|are|be)\s*$',previous['text'],re.I)
            connective=re.match(r'(?:therefore|thus|hence)\b',unit['text'],re.I)
            question_fragment=previous['text'].endswith('?') and re.match(r'(?:For|To)\s+(?!example\b)',unit['text'])
            if (dangling_aux and connective) or question_fragment:
                previous['end']=unit['end'];previous['text']=source[unit['source']][previous['start']:previous['end']]
                if question_fragment:previous['protected_atomic']=True
                continue
        result.append(dict(unit))
    for index,unit in enumerate(result):unit['id']=index
    return result
