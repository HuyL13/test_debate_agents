import unittest
from verify import validate_verification,decide


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.candidates=[{'id':'c0','label':'L1','structural_score':1,'retrieval_score':.7}]
        self.output={'assessments':[{'candidate_id':'c0','mapping_status':'valid','mechanism':'present','author':'endorsed','defect':'supported','reason_code':'warrant_misuse','evidence':[0,1],'reason':'The offered warrant does not justify the conclusion.'}]}

    def test_reason_code_and_fields_must_agree(self):
        validate_verification(self.output,self.candidates,[{'id':0},{'id':1}])
        self.output['assessments'][0]['reason_code']='legitimate_support'
        with self.assertRaises(ValueError):validate_verification(self.output,self.candidates,[{'id':0},{'id':1}])

    def test_cannot_use_unknown_evidence(self):
        self.output['assessments'][0]['evidence']=[99]
        with self.assertRaises(ValueError):validate_verification(self.output,self.candidates,[{'id':0},{'id':1}])

    def test_rebuttal_is_selected_only_as_weak_mechanism(self):
        a=self.output['assessments'][0];a.update(author='challenged',defect='uncertain',reason_code='challenged_argument')
        result=decide(self.output,self.candidates)
        self.assertEqual(result['prediction'],'L1')
        self.assertEqual(result['selection_status'],'weak_candidate')

    def test_invalid_mapping_cannot_be_confirmed_from_global_topic(self):
        a=self.output['assessments'][0];a.update(mapping_status='invalid',mechanism='partial',defect='uncertain',reason_code='mapping_invalid')
        result=decide(self.output,self.candidates)
        self.assertEqual(result['scored_candidates'][0]['verification_score'],0)
        self.assertEqual(result['selection_status'],'forced_candidate')


if __name__=='__main__':unittest.main()
