import argparse
import collections
import contextlib
import io
import json
import random
from pathlib import Path
from core import ROOT,REPO,batch,extract,model_settings,render_report
from patterns import mine_patterns,retrieve,bootstrap_recovery
from refinements import PROMPT_V3

MODEL='nvidia/nemotron-3-super-120b-a12b'
VERSION='v3-compact'


def settings():
    out=model_settings(MODEL);out.update(max_tokens=8192,chat_template_kwargs={'enable_thinking':True,'reasoning_budget':1024});return out


def dataset(induction_count=20):
    data=json.loads((REPO/'data/cocolofa/classification/train.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT.parent/'run-live/samples.json').read_text(encoding='utf-8'))
    exposed={s['article_id'] for s in old}
    articles=sorted({s['article_id'] for s in data}-exposed)
    rng=random.Random(20261018);rng.shuffle(articles)
    sealed=set(articles[:90]);development=set(articles[90:180])|exposed
    result={'induction':[],'development':[],'sealed':[]}
    labels=sorted({s['gold'] for s in data})
    for split,count in [('induction',induction_count),('development',10),('sealed',10)]:
        for label in labels:
            pool=[s for s in data if s['gold']==label and ('sealed' if s['article_id'] in sealed else 'development' if s['article_id'] in development else 'induction')==split]
            rng.shuffle(pool);used=set();picked=[]
            for s in pool:
                if s['article_id'] in used:continue
                used.add(s['article_id']);picked.append(dict(s,split=split))
                if len(picked)==count:break
            if len(picked)!=count:raise ValueError('insufficient distinct-article samples for '+split+' '+label)
            result[split].extend(picked)
    assert not ({s['article_id'] for s in result['induction']}&{s['article_id'] for s in result['development']})
    assert not ({s['article_id'] for s in result['sealed']}&{s['article_id'] for s in result['induction']+result['development']})
    assert not ({s['article_id'] for s in result['sealed']}&exposed)
    return result


def run_extract(samples,version=VERSION,model=MODEL,workers=4):
    prompt=PROMPT_V3;unitizer=None
    if version.startswith('v4'):
        from refinements import PROMPT_V4
        from unitization import split_units_v4
        prompt=PROMPT_V4;unitizer=split_units_v4
    def run(s):
        out=extract(model,s,version,prompt=prompt,settings=settings(),unitizer=unitizer)
        return {**out,'gold':s['gold'],'article_id':s['article_id'],'split':s.get('split','diagnostic')}
    return batch(samples,run,'Real-source extraction',workers=workers)


def pattern_and_retrieval(rows):
    training=[r for r in rows if r['split']=='induction']
    patterns=mine_patterns(training);recovery=bootstrap_recovery(patterns,training)
    for p in patterns:p['bootstrap_recovery']=recovery[p['id']]
    # Freeze only repeatably recovered class patterns; retain rejected ones for inspection.
    stable=[p for p in patterns if p['bootstrap_recovery']>=.8]
    retrieved=[{'sample_id':r['sample_id'],'split':r['split'],'gold':r['gold'],'status':r['status'],'candidates':retrieve(stable,r)} for r in rows if r['split']!='induction']
    metrics={}
    for split in sorted({r['split'] for r in rows}):
        pool=[r for r in rows if r['split']==split];rs=[r for r in retrieved if r['split']==split]
        metrics[split]={'count':len(pool),'contract_valid':sum(r['status']=='accepted' for r in pool),'empty_graphs':sum(r['status']=='accepted' and not r['extraction']['arguments'] for r in pool),'per_label':{}}
        for label in sorted({r['gold'] for r in pool}):
            own=[r for r in pool if r['gold']==label];rr=[r for r in rs if r['gold']==label]
            metrics[split]['per_label'][label]={'count':len(own),'valid':sum(r['status']=='accepted' for r in own),'stable_patterns':sum(p['label']==label for p in stable),'candidate_gold_recall':sum(any(c['label']==label for c in r['candidates']) for r in rr)}
        if rs:metrics[split]['candidate_gold_recall']=sum(any(c['label']==r['gold'] for c in r['candidates']) for r in rs)/len(rs)
    return patterns,stable,retrieved,metrics


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--sealed',action='store_true');ap.add_argument('--version',choices=['v3','v4'],default='v3');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    if args.sealed and not (ROOT/'freeze.json').exists():raise ValueError('Freeze model/prompt/ontology after development gates before opening sealed validation')
    if args.diagnostic:
        samples=json.loads((ROOT.parent/'run-live/samples.json').read_text(encoding='utf-8'))
    else:
        splits=dataset();(ROOT/'partitions.json').write_text(json.dumps(splits,ensure_ascii=False,indent=2),encoding='utf-8')
        samples=splits['induction']+splits['development']+(splits['sealed'] if args.sealed else [])
    rows=run_extract(samples,version=args.version+'-compact',workers=args.workers)
    name='diagnostic_'+args.version if args.diagnostic else 'pipeline_'+args.version+'_sealed' if args.sealed else 'pipeline_'+args.version
    (ROOT/(name+'_graphs.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.diagnostic:
        metrics={'count':len(rows),'valid':sum(r['status']=='accepted' for r in rows),'empty':sum(r['status']=='accepted' and not r['extraction']['arguments'] for r in rows)}
        render_report(ROOT/'report.html',rows,metrics);print(json.dumps(metrics));return
    patterns,stable,retrieved,metrics=pattern_and_retrieval(rows)
    (ROOT/(name+'_patterns.json')).write_text(json.dumps({'all_patterns':patterns,'stable_patterns':stable},ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_retrieval.json')).write_text(json.dumps(retrieved,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/(name+'_metrics.json')).write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    render_report(ROOT/'report.html',{'graphs':rows,'patterns':stable,'retrieval':retrieved},metrics)
    print(json.dumps(metrics,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
