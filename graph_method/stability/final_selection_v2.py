"""Selective final contract; benchmark type and author-fallacy evidence differ."""

def select(decision,mode='classification'):
    if mode not in ['classification','author_fallacy']:raise ValueError('unknown selection task')
    candidates=decision.get('scored_candidates',[])
    eligible=[c for c in candidates if c.get('direction_matches') and c['assessment']['mapping_status']=='valid' and c['assessment']['mechanism']=='present']
    if mode=='author_fallacy':eligible=[c for c in eligible if c.get('confirmed')]
    if not eligible:return dict(prediction=None,best_candidate_id=None,selection_status='no_supported_candidate',author_fallacy_confirmed=False,mode=mode)
    best=eligible[0]
    return dict(prediction=best['label'],best_candidate_id=best['id'],selection_status='confirmed_author_fallacy' if best.get('confirmed') else 'type_candidate_only',author_fallacy_confirmed=bool(best.get('confirmed')),mode=mode)
