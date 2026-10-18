import unittest
from reviewed_training_v2 import graph_fingerprint,admit_training
from test_patterns_v2 import fixture

class ReviewedTrainingTests(unittest.TestCase):
    def test_llm_source_agreement_alone_does_not_approve_pattern_training(self):
        row=fixture();row['semantic_review']={'status':'accepted','decisions':{'a0':{'verdict':'supported'}}}
        kept,rejected=admit_training([row],[])
        self.assertEqual(kept,[]);self.assertTrue(rejected)
    def approval(self,row):
        return dict(sample_id=row['sample_id'],graph_sha256=graph_fingerprint(row),reviewer='reviewer-example',reviewer_type='human',checks={k:True for k in ['source_relations','central_coverage','speaker_stance','negation_modality','warrant_roles']})
    def test_full_review_accepts_exact_snapshot(self):
        row=fixture();kept,rejected=admit_training([row],[self.approval(row)])
        self.assertEqual(len(kept),1);self.assertEqual(rejected,[])
    def test_changed_graph_invalidates_approval(self):
        row=fixture();approval=self.approval(row);row['annotation']['applications'][0]['scheme']='other'
        self.assertFalse(admit_training([row],[approval])[0])
    def test_silver_is_explicitly_separate_from_expert_gold(self):
        row=fixture();approval=self.approval(row);approval['reviewer_type']='assistant_silver'
        self.assertFalse(admit_training([row],[approval])[0])
        self.assertEqual(len(admit_training([row],[approval],allow_silver=True)[0]),1)
    def test_bank_exports_measured_bootstrap_recovery(self):
        from reviewed_training_v2 import build_bank
        rows=[fixture(article=i) for i in range(40)]
        result=build_bank(rows,[self.approval(r) for r in rows])
        self.assertTrue(result['patterns'])
        self.assertGreaterEqual(result['patterns'][0]['bootstrap_recovery'],.8)
        self.assertFalse(result['ready_for_full_label_matching'])
    def test_reviewed_train_snapshot_can_override_rejected_model_proposal(self):
        from reviewed_training_v2 import build_bank
        rows=[fixture(article=i) for i in range(40)]
        for row in rows:
            row['semantic_review_required']=True
            row['semantic_review']={'decisions':{'a0':{'verdict':'unsupported'}}}
        result=build_bank(rows,[self.approval(r) for r in rows])
        self.assertTrue(result['patterns'])
        self.assertEqual(rows[0]['semantic_review']['decisions']['a0']['verdict'],'unsupported')
