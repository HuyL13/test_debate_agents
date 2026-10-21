import unittest
from unittest.mock import Mock
from roundtrip_resume import verbalize, review_needed, choose_existing, process_one

class RoundtripTests(unittest.TestCase):
    def test_minor_review_does_not_regenerate(self):
        row={'status':'accepted','graph':{},'annotation':{}}
        extract=Mock(return_value=row);review=Mock(return_value={'status':'accepted','assessment':{'verdict':'minor'}})
        result=process_one({'sample_id':'x'},'model',extract_fn=extract,review_fn=review)
        self.assertEqual(result['status'],'accepted');self.assertEqual(extract.call_count,1)
    def test_major_repairs_once_and_keeps_flagged_graph(self):
        extract=Mock(side_effect=[{'status':'accepted','graph':{},'annotation':{}},{'status':'accepted','graph':{},'annotation':{}}])
        review=Mock(return_value={'status':'accepted','reading':'reading','assessment':{'verdict':'major'}})
        result=process_one({'sample_id':'x'},'model',extract_fn=extract,review_fn=review)
        self.assertEqual(extract.call_count,2);self.assertEqual(result['status'],'accepted')
        self.assertEqual(result['roundtrip']['warning'],'alignment_unresolved')
    def test_review_network_failure_never_rejects_graph(self):
        extract=Mock(return_value={'status':'accepted','graph':{},'annotation':{}})
        review=Mock(return_value={'status':'infrastructure_error','assessment':None})
        result=process_one({'sample_id':'x'},'model',extract_fn=extract,review_fn=review)
        self.assertEqual(result['status'],'accepted');self.assertEqual(extract.call_count,1)
    def test_only_valid_existing_graphs_skip(self):
        self.assertTrue(choose_existing({'status':'accepted','graph':{'nodes':[]},'annotation':{}}))
        self.assertFalse(choose_existing({'status':'typing_failed','graph':{'nodes':[]}}))
    def test_only_major_mismatch_requests_repair(self):
        for verdict in ['aligned','minor','unclear']:
            self.assertFalse(review_needed({'verdict':verdict}))
        self.assertTrue(review_needed({'verdict':'major'}))
    def test_verbalization_preserves_direction_and_facets(self):
        row={'graph':{'nodes':[{'type':'Proposition','id':'p0','content':'does not act','owner':'current_author','speech_act':'hypothetical','modality':'possible','polarity':'negative','event_role':'condition'}]},'annotation':{'applications':[{'kind':'projection','premises':[0],'target_kind':'proposition','target':1,'scheme':'causal_projection','stance':'uses','roles':[{'role':'initial','proposition':0}],'scope_change':'na','alternatives':'na'}]}}
        text=verbalize(row)
        for value in ['does not act','negative','possible','p0','p1','projection','initial']:
            self.assertIn(value,text)

if __name__=='__main__':unittest.main()
