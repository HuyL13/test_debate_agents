import unittest
from experiment_v2 import pattern_stage
from test_patterns_v2 import fixture


class CompletePipelineIntegrationTests(unittest.TestCase):
    def test_patterns_learn_only_from_training_articles(self):
        training=[fixture(i,'A') for i in range(25)]
        validation=[dict(fixture(i+100,'VALIDATION_ONLY'),split='development') for i in range(10)]
        result=pattern_stage(training+validation)
        self.assertTrue(result['patterns'])
        self.assertEqual({p['label'] for p in result['patterns']},{'A'})
        self.assertEqual(len(result['retrieval']),10)

    def test_source_failure_remains_in_candidate_recall_denominator(self):
        training=[fixture(i,'A') for i in range(25)]
        good=dict(fixture(100,'A'),split='development')
        failed=dict(fixture(101,'A'),split='development',status='witness_failed',annotation=None)
        result=pattern_stage(training+[good,failed])
        self.assertIn('development',result['metrics'])
        self.assertEqual(result['metrics']['development']['count'],2)
        self.assertEqual(result['metrics']['development']['candidate_gold_recall'],.5)
        self.assertEqual(len(result['retrieval'][1]['candidates']),0)

    def test_missing_supported_label_is_explicit_in_merged_exports(self):
        rows=[fixture(i,'A') for i in range(25)]+[fixture(100,'B')]
        result=pattern_stage(rows)
        self.assertIn('B',result['merged_pattern_graphs'])
        self.assertEqual(result['merged_pattern_graphs']['B']['status'],'insufficient_supported_patterns')
        self.assertEqual(result['merged_pattern_graphs']['B']['prototypes'],[])


if __name__=='__main__':unittest.main()
