import unittest
from evaluate_v2 import stage_contract_metrics

class ReviewStageReporting(unittest.TestCase):
    def test_local_json_cleanup_does_not_count_as_raw_first_pass(self):
        row={'stage_status':{'warrant':'accepted'},'stage_call_ids':{'warrant':'x'}}
        record={'attempts':[{'status':'accepted','syntax_normalization':'extra closing brace'}]}
        metric=stage_contract_metrics([row],{'x':record})['warrant']
        self.assertEqual(metric['first_contract_response_valid'],0)
        self.assertEqual(metric['locally_normalized_attempts'],1)
    def test_empty_graph_review_is_not_unreached(self):
        row={'stage_status':{},'semantic_review':{'status':'not_applicable','call_id':None,'decisions':{}}}
        metric=stage_contract_metrics([row],{})['semantic_review']
        self.assertEqual(metric['not_applicable'],1)
        self.assertEqual(metric['not_reached'],0)
class StageContractMetricsTests(unittest.TestCase):
    def test_retry_cannot_hide_first_response_failure(self):
        rows=[dict(stage_status={'proposal':'accepted'},stage_call_ids={'proposal':'c'})]
        records={'c':dict(attempts=[dict(status='quality_rejected'),dict(status='accepted')])}
        s=stage_contract_metrics(rows,records)['proposal']
        self.assertEqual(s['final_valid'],1);self.assertEqual(s['first_contract_response_valid'],0);self.assertEqual(s['quality_rejected_attempts'],1)
    def test_transport_failure_is_separate_from_first_contract_response(self):
        rows=[dict(stage_status={'witness':'accepted'},stage_call_ids={'witness':'c'})]
        records={'c':dict(attempts=[dict(status='infrastructure_error'),dict(status='accepted')])}
        s=stage_contract_metrics(rows,records)['witness']
        self.assertEqual(s['first_contract_response_valid'],1);self.assertEqual(s['infrastructure_error_attempts'],1)
    def test_not_reached_and_missing_records_remain_in_expected_denominator(self):
        rows=[dict(stage_status={'proposal':'accepted','warrant':'not_reached'},stage_call_ids={'proposal':'missing','warrant':None})]
        m=stage_contract_metrics(rows,{},expected=4)
        self.assertEqual(m['proposal']['expected'],4);self.assertEqual(m['proposal']['missing_call_records'],1)
        self.assertEqual(m['warrant']['not_reached'],1);self.assertEqual(m['warrant']['final_valid'],0)
