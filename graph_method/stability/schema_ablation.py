"""Isolate schema coupling and reasoning budget on audited real sources."""
import argparse
import json
from copy import deepcopy
from core import ROOT,invoke,batch,compile_graph
from pipeline import MODEL,settings,dataset
from structured import extraction_schema,validate
from refinements import PROMPT_V8
from normalization import normalize


def simple_schema(units):
    original=extraction_schema(units)
    first=original['properties']['arguments']['items']['anyOf'][0]
    props=deepcopy(first['properties']);ids=[u['id'] for u in units]
    props['conclusion']={'type':'integer','enum':[u['id'] for u in units if u['source']!='title']}
    props['premises']['items']['enum']=ids;props['premises']['maxItems']=len(ids)
    props={'conclusion':props.pop('conclusion'),**props}
    original['properties']['arguments']['items']={'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
    return original


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--schema',choices=['simple','coupled'],required=True);parser.add_argument('--budget',type=int,default=1024);parser.add_argument('--model',default=MODEL);parser.add_argument('--samples',nargs='+');parser.add_argument('--format',choices=['json_schema','json_object','plain'],default='json_schema');args=parser.parse_args()
    partial=json.loads((ROOT/'pipeline_v12_partial_graphs.json').read_text(encoding='utf-8'))['rows']
    source_map={s['sample_id']:s for s in dataset(40)['induction']}
    selected=[]
    for label in sorted({r['gold'] for r in partial}):
        target=next(s['sample_id'] for s in dataset(40)['induction'] if s['gold']==label)
        selected.append(next(r for r in partial if r['sample_id']==target))
    if args.samples:selected=[r for r in selected if r['sample_id'] in args.samples]
    version='ablation-'+args.schema+'-b'+str(args.budget)
    if args.model!=MODEL:version+='-'+args.model.split('/')[-1]
    if args.format!='json_schema':version+='-'+args.format
    def run(row):
        source=source_map[row['sample_id']];units=row['units'];config=settings()
        config['chat_template_kwargs']['reasoning_budget']=args.budget
        config['response_format']={'type':'json_schema','json_schema':{'name':'grounded_argument','strict':True,'schema':simple_schema(units) if args.schema=='simple' else extraction_schema(units)}}
        if 'nemotron-3' not in args.model:config.pop('chat_template_kwargs',None)
        if args.format=='json_object':config['response_format']={'type':'json_object'}
        elif args.format=='plain':config.pop('response_format',None)
        rec=invoke(args.model,'extract',row['sample_id'],PROMPT_V8,{'source':{k:source.get(k,'') for k in ['comment','title','parent_comment']},'units':units},lambda o:validate(o,units),version,settings=config)
        extraction,changes=normalize(rec['output'],units) if rec['status']=='accepted' else (None,[])
        return {'sample_id':row['sample_id'],'gold':row['gold'],'status':rec['status'],'source_call_id':rec['call_id'],'units':units,'extraction':extraction,'normalization':changes,'graph':compile_graph(extraction,units) if extraction else None,'baseline_v12_extraction':row['extraction']}
    rows=batch(selected,run,version,workers=2)
    (ROOT/(version+'_graphs.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'count':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'empty':sum(r['status']=='accepted' and not r['extraction']['arguments'] for r in rows)},indent=2),flush=True)


if __name__=='__main__':main()
