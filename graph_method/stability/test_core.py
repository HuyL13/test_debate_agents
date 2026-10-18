import unittest
from core import compile_graph,validate_extraction,cache_identity,split_units


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.units=split_units({'comment':'Most people believe it, so it must be correct.','title':'','parent_comment':''})

    def output(self):
        return {'arguments':[{'premises':[0],'conclusion':1,'operator':'consensus','stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[]}]}

    def test_clause_offsets_are_exact(self):
        self.assertEqual(len(self.units),2)
        text='Most people believe it, so it must be correct.'
        for u in self.units:self.assertEqual(text[u['start']:u['end']],u['text'])

    def test_self_premise_and_missing_ids_rejected(self):
        o=self.output();validate_extraction(o,self.units)
        o['arguments'][0]['conclusion']=0
        with self.assertRaises(ValueError):validate_extraction(o,self.units)
        o['arguments'][0]['conclusion']=99
        with self.assertRaises(ValueError):validate_extraction(o,self.units)

    def test_neutral_operator_is_on_inference_not_source(self):
        g=compile_graph(self.output(),self.units)
        inference=next(n for n in g['nodes'] if n['kind']=='inference')
        self.assertEqual(inference['operator'],'consensus')
        self.assertTrue(all('operator' not in n for n in g['nodes'] if n['kind']=='proposition'))

    def test_cache_distinguishes_models_and_settings(self):
        a=cache_identity('modelA',{},'s',{'x':1})
        self.assertNotEqual(a,cache_identity('modelB',{},'s',{'x':1}))
        self.assertNotEqual(a,cache_identity('modelA',{'thinking':True},'s',{'x':1}))


if __name__=='__main__':unittest.main()
