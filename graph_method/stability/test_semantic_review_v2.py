import unittest
from semantic_review_v2 import validate_review,eligible_application

class SemanticReviewTests(unittest.TestCase):
    def test_supported_requires_independent_same_direction(self):
        apps=[dict(premises=[0],target_kind='proposition',target=1,kind='support',stance='uses')]
        decision=dict(verdict='supported',premises=['p1'],target_kind='proposition',target='p0',kind='support',stance='uses',evidence_units=[0],reason='reversed')
        with self.assertRaises(ValueError):validate_review({'a0':decision},apps,[{'id':0}])
    def test_application_target_dependency_must_be_confirmed(self):
        row={'annotation':{'applications':[dict(target_kind='application',target=1),dict(target_kind='proposition',target=0)]},'semantic_review':{'decisions':{'a0':{'verdict':'supported'},'a1':{'verdict':'unclear'}}}}
        self.assertFalse(eligible_application(row,0))
        row['semantic_review']['decisions']['a1']['verdict']='supported'
        self.assertTrue(eligible_application(row,0))
    def test_absent_required_review_is_not_eligible(self):
        self.assertFalse(eligible_application({'semantic_review_required':True,'annotation':{'applications':[]}},0))
    def test_legacy_rows_preserve_explicit_old_policy(self):
        self.assertTrue(eligible_application({'annotation':{'applications':[]}},0))
