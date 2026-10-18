import copy
import unittest
from patterns_v2 import mine_patterns,retrieve
from test_patterns_v2 import fixture
import verify_v2
from verify_v2 import validate_verification,decide


class Verification(unittest.TestCase):
    def test_strict_candidate_keyed_schema_keeps_independent_endpoints(self):
        schema=verify_v2.verification_schema(self.cs,self.row)
        assessment=schema['properties']['assessments']
        self.assertEqual(assessment['required'],['c0'])
        fields=assessment['properties']['c0']['properties']
        self.assertNotIn('const',fields['witnessed_target_id'])
        self.assertIn('none',fields['witnessed_target_kind']['enum'])
        raw={'assessments':{'c0':{k:v for k,v in self.output['assessments'][0].items() if k!='candidate_id'}}}
        self.assertEqual(verify_v2.canonicalize(raw),self.output)
    def setUp(self):
        self.row=fixture(90);self.cs=retrieve(mine_patterns([fixture(i) for i in range(8)]),self.row,min_bootstrap=0)
        self.output={'assessments':[{'candidate_id':'c0','mapping_status':'valid','witnessed_premises':[0,1],'witnessed_target_kind':'proposition','witnessed_target_id':2,'witnessed_kind':'support','mechanism':'present','author':'endorsed','defect':'supported','reason_code':'warrant_misuse','evidence':[{'unit':0,'first':0,'last':1}],'reason':'Status alone warrants this claim.'}]}

    def test_confirmed(self):
        validate_verification(self.output,self.cs,self.row)
        self.assertEqual(decide(self.output,self.cs)['selection_status'],'confirmed')

    def test_wrong_direction_rejected(self):
        self.output['assessments'][0]['witnessed_target_id']=0
        with self.assertRaises(ValueError):validate_verification(self.output,self.cs,self.row)
        self.assertFalse(decide(self.output,self.cs)['scored_candidates'][0]['confirmed'])

    def test_bad_evidence_and_confidence_only_rejected(self):
        broken=copy.deepcopy(self.output);broken['assessments'][0]['evidence'][0]['last']=99
        with self.assertRaises(ValueError):validate_verification(broken,self.cs,self.row)
        with self.assertRaises(ValueError):validate_verification({'assessments':[{'candidate_id':'c0','confidence':1}]},self.cs,self.row)

    def test_challenged_never_confirmed(self):
        a=self.output['assessments'][0];a.update(author='challenged',defect='absent',reason_code='challenged_argument')
        validate_verification(self.output,self.cs,self.row)
        self.assertNotEqual(decide(self.output,self.cs)['selection_status'],'confirmed')

    def test_independent_witness_can_reject_support_as_actual_concession(self):
        a=self.output['assessments'][0];a.update(witnessed_kind='concession',mapping_status='invalid',mechanism='absent',defect='absent',reason_code='mapping_invalid')
        validate_verification(self.output,self.cs,self.row)
        self.assertFalse(decide(self.output,self.cs)['scored_candidates'][0]['confirmed'])

    def test_raw_verifier_call_is_traceable_from_final_selection(self):
        from unittest.mock import patch
        raw={'assessments':{'c0':{k:v for k,v in self.output['assessments'][0].items() if k!='candidate_id'}}}
        def fake(model,stage,sid,prompt,payload,validator,version,repeat,config):
            validator(raw)
            self.assertEqual(payload['annotation']['propositions'][0]['text'],'one')
            return dict(status='accepted',call_id='verifier-call',output=raw)
        with patch('core.invoke',side_effect=fake):out=verify_v2.verify(self.row,dict(comment='one two three'),self.cs)
        self.assertEqual(out['verification_call_id'],'verifier-call')

    def test_best_candidate_can_be_a_later_subgraph_of_the_same_label(self):
        c=copy.deepcopy(self.cs[0]);c.update(id='c1',premise_proposition_ids=[3,4],target_id=5,application_index=1)
        second=copy.deepcopy(self.output['assessments'][0]);second.update(candidate_id='c1',witnessed_premises=[3,4],witnessed_target_id=5)
        first=copy.deepcopy(self.output['assessments'][0]);first.update(mechanism='absent',defect='absent',reason_code='mechanism_missing')
        out=decide({'assessments':[first,second]},self.cs+[c])
        self.assertEqual(out['best_candidate_id'],'c1');self.assertEqual(out['selection_status'],'confirmed')

if __name__=='__main__':unittest.main()
