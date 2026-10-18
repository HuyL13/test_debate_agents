import unittest
from pattern_export import merge_pattern_graphs

class ExportTests(unittest.TestCase):
    def test_alternative_templates_do_not_get_false_reasoning_links(self):
        graph={'nodes':[{'id':'premise','kind':'proposition'},{'id':'inference','kind':'inference'},{'id':'conclusion','kind':'proposition'}],'edges':[{'src':'premise','rel':'PREMISE_OF','dst':'inference'},{'src':'inference','rel':'CONCLUDES','dst':'conclusion'}]}
        patterns=[{'id':str(i),'label':'L','graph':graph,'constraints':{'operator':'testimony'},'positive_articles':5,'bootstrap_recovery':.9,'witnesses':[]} for i in range(2)]
        merged=merge_pattern_graphs(patterns,['L','missing'])
        self.assertEqual(len(merged['L']['nodes']),9)
        self.assertEqual(len([e for e in merged['L']['edges'] if e['rel']=='PREMISE_OF']),2)
        self.assertEqual(merged['missing']['status'],'no_stable_pattern')
