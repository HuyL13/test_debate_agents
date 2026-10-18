import json
from core import ROOT,invoke
from atomic_tokens import atomize
from pipeline import MODEL
from refinements import PROMPT_V6
from structured import settings_for,validate

samples=json.loads((ROOT.parent/'run-live/samples.json').read_text(encoding='utf-8'))
sample=next(s for s in samples if s['sample_id']=='328:6382')
atom=atomize(sample);units=atom['units']
record=invoke(MODEL,'extract',sample['sample_id'],PROMPT_V6+'\nDo not invent extra arguments from title/context. Only grounded non-self premise/conclusion moves are allowed. Titles cannot be comment-author conclusion anchors.',{'source':{k:sample.get(k,'') for k in ['comment','title','parent_comment']},'units':units},lambda o:validate(o,units),'v8-structured-probe',settings=settings_for(units))
print(json.dumps({'status':record['status'],'attempts':len(record['attempts']),'output':record.get('output'),'errors':[a['rejection_reasons'] for a in record['attempts']]},ensure_ascii=False,indent=2))
