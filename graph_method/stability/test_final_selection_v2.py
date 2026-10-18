import unittest
from final_selection_v2 import select

class FinalSelectionTests(unittest.TestCase):
    def candidate(self,valid=True,confirmed=False):
        return dict(id='c0',label='False Dilemma',direction_matches=valid,confirmed=confirmed,assessment=dict(mapping_status='valid' if valid else 'invalid',mechanism='present',author='challenged',defect='uncertain'))
    def test_invalid_candidates_do_not_force_public_prediction(self):
        result=select({'scored_candidates':[self.candidate(False)]})
        self.assertIsNone(result['prediction']);self.assertEqual(result['selection_status'],'no_supported_candidate')
    def test_type_prediction_does_not_claim_author_fallacy(self):
        result=select({'scored_candidates':[self.candidate()]})
        self.assertEqual(result['prediction'],'False Dilemma');self.assertFalse(result['author_fallacy_confirmed'])
    def test_author_detection_requires_confirmed_defect(self):
        result=select({'scored_candidates':[self.candidate()]},mode='author_fallacy')
        self.assertIsNone(result['prediction'])
    def test_later_valid_candidate_can_replace_invalid_head(self):
        bad=self.candidate(False);good=self.candidate();good['id']='c1'
        self.assertEqual(select({'scored_candidates':[bad,good]})['best_candidate_id'],'c1')
