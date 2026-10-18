import unittest
from pair_source_v2 import pair_inventory,bind_pairs
from ontology_v2 import source_units
from decomposed_source_v2 import prepare_propositions

class PairSourceTests(unittest.TestCase):
    def setup_source(self):
        units=source_units(dict(comment='The rule harms people. We should change it.',title='Officials issued a rule.',parent_comment=''))
        raw={'propositions':[dict(unit=u['id'],quote=u['text'],owner='current_author' if u['source']=='comment' else 'context',speech_act='assert',modality='unspecified',polarity='positive',event_role='none',implicit=False,gloss='') for u in units]}
        return units,prepare_propositions(raw,units)
    def test_pairs_are_code_owned_and_context_is_not_a_premise(self):
        units,ps=self.setup_source();pairs=pair_inventory(ps,units)
        self.assertTrue(pairs)
        self.assertTrue(all(p['premise']!=p['target'] for p in pairs))
        self.assertTrue(all(ps[p['premise']]['owner']=='current_author' for p in pairs))
    def test_none_does_not_create_edge_and_direction_is_immutable(self):
        units,ps=self.setup_source();pairs=pair_inventory(ps,units)
        raw={p['id']:dict(relation='none',stance='unclear',reason='not offered') for p in pairs}
        selected=next(p for p in pairs if p['premise']==0 and p['target']==1)
        raw[selected['id']]=dict(relation='support',stance='uses',reason='harm is the offered reason to change')
        ann=bind_pairs(raw,ps,units,pairs)
        self.assertEqual(len(ann['applications']),1)
        self.assertEqual(ann['applications'][0]['premises'],[0]);self.assertEqual(ann['applications'][0]['target'],1)
    def test_missing_pair_is_a_failure_not_a_negative(self):
        units,ps=self.setup_source()
        with self.assertRaises(ValueError):bind_pairs({},ps,units,pair_inventory(ps,units))
    def test_failed_pair_stage_keeps_its_status_and_call_id(self):
        from pair_source_v2 import process
        from source_quotes_v2 import annotation_to_quotes
        units,ps=self.setup_source()
        raw=annotation_to_quotes({'propositions':ps,'applications':[]},units)
        raw={'propositions':[{k:v for k,v in p.items() if k not in ['id','occurrence']} for p in raw['propositions']]}
        def invoke(model,stage,*args,**kwargs):
            return dict(status='accepted',call_id='ps',output=raw) if stage=='source_propositions_v2' else dict(status='quality_rejected',call_id='pair')
        row=process(dict(sample_id='x',comment='The rule harms people. We should change it.',title='Officials issued a rule.',parent_comment=''),invoke_fn=invoke)
        self.assertEqual(row['stage_status']['witness'],'quality_rejected')
        self.assertEqual(row['stage_call_ids']['witness'],'pair')
