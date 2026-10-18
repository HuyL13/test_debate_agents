"""Reviewed TRAIN admission. An approval is a record, not semantic proof.

Never synthesize reviewer approvals from class labels or LLM agreement. Default
requires human review; assistant silver is an explicit research-only opt-in.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from patterns_v2 import mine_patterns,bootstrap_recovery

CHECKS={'source_relations','central_coverage','speaker_stance','negation_modality','warrant_roles'}

def graph_fingerprint(row):
    snapshot={k:row.get(k) for k in ['sample_id','article_id','gold','units','annotation']}
    return hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def admit_training(rows,approvals,allow_silver=False):
    approved={a['sample_id']:a for a in approvals};kept=[];rejected=[]
    for row in rows:
        a=approved.get(row['sample_id']);reason=None
        if row.get('split')!='induction':reason='not_induction_train'
        elif row.get('status')!='accepted' or not row.get('annotation'):reason='source_graph_failed'
        elif not a:reason='missing_review'
        elif a.get('graph_sha256')!=graph_fingerprint(row):reason='review_snapshot_mismatch'
        elif not a.get('reviewer'):reason='missing_reviewer'
        elif a.get('reviewer_type') not in (['human','assistant_silver'] if allow_silver else ['human']):reason='review_not_expert_gold'
        elif set(a.get('checks',{}))!=CHECKS or any(v is not True for v in a['checks'].values()):reason='review_incomplete_or_unresolved'
        if reason:rejected.append(dict(sample_id=row['sample_id'],reason=reason))
        else:
            # A reviewed snapshot is a separate admission tier. Preserve the
            # model's rejected/unclear review without relabeling it supported.
            reviewed=deepcopy(row)
            reviewed['automatic_source_review']=reviewed.pop('semantic_review',None)
            reviewed['semantic_review_required']=False
            reviewed['training_review']=deepcopy(a)
            kept.append(reviewed)
    return kept,rejected

def build_bank(rows,approvals,allow_silver=False):
    kept,rejected=admit_training(rows,approvals,allow_silver)
    patterns=mine_patterns(kept);recovery=bootstrap_recovery(patterns,kept)
    for pattern in patterns:pattern['bootstrap_recovery']=recovery[pattern['id']]
    labels=sorted({r['gold'] for r in rows if r.get('split')=='induction'});supported={p['label'] for p in patterns if p.get('bootstrap_recovery',0)>=.8}
    return dict(policy='reviewed_train_silver_opt_in' if allow_silver else 'reviewed_train_human',accepted_graphs=len(kept),rejected=rejected,missing_supported_labels=[l for l in labels if l not in supported],patterns=patterns,ready_for_full_label_matching=len(labels)==8 and set(labels)<=supported)

def main():
    p=argparse.ArgumentParser();p.add_argument('graphs');p.add_argument('approvals');p.add_argument('--output',default='reviewed_pattern_bank.json');p.add_argument('--allow-silver',action='store_true');args=p.parse_args()
    rows=json.loads(Path(args.graphs).read_text(encoding='utf-8'));approvals=json.loads(Path(args.approvals).read_text(encoding='utf-8'))
    result=build_bank(rows,approvals,args.allow_silver)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['patterns','rejected']},indent=2))

if __name__=='__main__':main()
