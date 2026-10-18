import unittest
from fewshot_source_v2 import examples
from ontology_v2 import compile_graph
class SourceDemonstrations(unittest.TestCase):
    def test_rejected_warrant_is_hypothesized_and_undercut_targets_application(self):
        e=examples()[0];a=e['annotation'];g=compile_graph(a,e['units'])
        self.assertEqual(a['applications'][1]['target_kind'],'application')
        self.assertEqual(a['applications'][1]['target'],0)
        for i in [1,2]:self.assertTrue(any(edge['source']=='assertion'+str(i) and edge['type']=='HYPOTHESIZES' for edge in g['edges']))
    def test_projected_risk_and_normative_recommendation_are_distinct(self):
        e=examples()[1];a=e['annotation']
        self.assertEqual([(x['kind'],x['premises'],x['target']) for x in a['applications']],[('projection',[0],1),('support',[1],2)])
        self.assertEqual(a['propositions'][1]['modality'],'possible')
        self.assertEqual(a['propositions'][2]['speech_act'],'recommend')
        self.assertEqual(a['propositions'][2]['event_role'],'none')

    def test_concession_is_separate_from_the_offered_harm_reason(self):
        a=examples()[2]['annotation']
        self.assertEqual([(x['kind'],x['premises'],x['target']) for x in a['applications']],[('concession',[0],1),('support',[2],1)])
    def test_exhaustive_choices_have_distinct_literal_bindings(self):
        a=examples()[3]['annotation']
        self.assertEqual({r['proposition'] for r in a['applications'][0]['roles'] if r['role']=='choice'},{1,2})
    def test_conflicting_reports_do_not_become_projected_events(self):
        a=examples()[4]['annotation']
        self.assertEqual([x['kind'] for x in a['applications']],['rebut','support'])
        self.assertTrue(all(p['event_role']=='none' for p in a['propositions']))
