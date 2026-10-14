"""Private V3 ledger adapter for the existing bounded delta reward engine."""
import numpy as np
from copy import deepcopy
from src.courtroom_rl.reward import RewardEngine as ComponentReward, grounded_spans


class RewardEngine(ComponentReward):
    version='action-centric-component-delta-v1'

    def transition(self,state,event,input_tokens,output_tokens,calls):
        adapted=deepcopy(event)
        # The inherited wrong-charge gate must also cover V3 support arguments,
        # since those labels are now selected by the executor, not by an actor.
        if event['action']=='DEFEND_CLAIM':
            adapted['action']='ACCUSE'
            adapted['target']=event.get('payload',{}).get('label')
        return super().transition(state,adapted,input_tokens,output_tokens,calls)

    def _board(self,state):
        units={}
        for claim in state.claims:
            spans=grounded_spans({'evidence_spans':claim.evidence_spans},state)
            if not spans:continue
            # Grounding and class/kind consistency are proxies, not proof that
            # any generated argument is logically valid.
            consistent=(claim.kind=='CONTRADICTING' and claim.label!=self._gold) or (
                claim.kind in ('SUPPORTING','REBUTTAL') and claim.label==self._gold)
            if claim.kind=='SUPPORTING' and claim.label!=self._gold and claim.status=='DISPUTED':
                consistent=any(c.kind=='CONTRADICTING' and c.hypothesis_id==claim.hypothesis_id for c in state.claims)
            for span in spans:
                key=(claim.label,span)
                units[key]=max(units.get(key,0.),float(consistent))
        return float(np.mean(list(units.values()))) if units else 0.
