import unittest
from normalization import normalize,review_flags


class NormalizationTests(unittest.TestCase):
    def argument(self,**kwargs):
        return {'premises':[0],'conclusion':1,'operator':'testimony','stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[],**kwargs}

    def test_explicit_possibility_is_not_promoted_to_certainty(self):
        units=[{'id':0,'text':'An expert says it might help.'},{'id':1,'text':'Therefore it might be worth trying.'}]
        out,changes=normalize({'arguments':[self.argument()]},units)
        self.assertEqual(out['arguments'][0]['commitment'],'possible')
        self.assertEqual(changes[0]['anchor_unit_id'],1)

    def test_should_is_normative_but_epistemic_must_is_not(self):
        for text,expected in [('Therefore we should try it.','normative'),('Therefore it must be true.','certain')]:
            out,_=normalize({'arguments':[self.argument()]},[{'id':0,'text':'Expert says so.'},{'id':1,'text':text}])
            self.assertEqual(out['arguments'][0]['commitment'],expected)

    def test_denial_is_not_a_prescription(self):
        units=[{'id':0,'text':'Others want it.'},{'id':1,'text':'That does not mean we should accept it.'}]
        out,_=normalize({'arguments':[self.argument(stance='critiques')]},units)
        self.assertEqual(out['arguments'][0]['commitment'],'certain')

    def test_flags_request_review_without_inventing_operator(self):
        units=[{'id':0,'text':'A is less important than B.'},{'id':1,'text':'Ignore A.'}]
        out={'arguments':[self.argument(operator='evidence')]}
        flags=review_flags(out,units)
        self.assertTrue(flags)
        self.assertEqual(out['arguments'][0]['operator'],'evidence')

    def test_missing_critique_is_reviewed_without_changing_stance(self):
        units=[{'id':0,'text':'Some insist only A or B.'},{'id':1,'text':'Those are not our only choices.'}]
        out={'arguments':[self.argument(operator='alternatives',alternatives='open')]}
        flags=review_flags(out,units,include_critique=True)
        self.assertTrue(any('rejection' in flag for flag in flags))
        self.assertEqual(out['arguments'][0]['stance'],'uses')


if __name__=='__main__':unittest.main()
