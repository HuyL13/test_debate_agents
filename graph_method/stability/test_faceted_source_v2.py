import importlib.util
import unittest
from ontology_v2 import source_units, proposition_span
from decomposed_source_v2 import prepare_propositions

@unittest.skipUnless(importlib.util.find_spec('en_core_web_sm'),'requires syntax environment')
class EventInventoryTests(unittest.TestCase):
    def inventory(self,text):
        from faceted_source_v2 import event_inventory
        units=source_units({'comment':text,'title':'','parent_comment':''})
        raw={'propositions':[dict(unit=u['id'],quote=u['text'],owner='current_author',speech_act='assert',modality='unspecified',polarity='positive',event_role='none',implicit=False,gloss='') for u in units]}
        ps=prepare_propositions(raw,units)
        return units,event_inventory(ps,units)
    def test_deictic_forecast_excludes_meta_and_following_recommendation(self):
        units,(ps,profiles,qs)=self.inventory("It's a thin line. Should politicians be allowed to block abusive users? This might lead to a politician blocking all critics. We should protect speech.")
        self.assertEqual(len(qs),1)
        q=qs[0]
        self.assertNotIn('p0',q['eligible_initials'])
        self.assertIn('p1',q['eligible_initials'])
        self.assertNotIn('p3',q['eligible_initials'])
        effect=ps[int(q['target'][1:])]
        self.assertIn('blocking all critics',proposition_span(effect,units)['text'])
        self.assertEqual(effect['speech_act'],'hypothetical')
        self.assertEqual(effect['modality'],'possible')
    def test_epistemic_and_approval_do_not_create_forecasts(self):
        _,(_,_,qs)=self.inventory('We cannot trust the agency if it concealed evidence. If they return it, great.')
        self.assertEqual(qs,[])
    def test_explicit_condition_is_available_in_same_unit(self):
        units,(ps,_,qs)=self.inventory('If the river rises, nearby homes will flood.')
        self.assertEqual(len(qs),1)
        self.assertTrue(any('river rises' in proposition_span(ps[int(pid[1:])],units)['text'] for pid in qs[0]['eligible_initials']))
    def test_negated_causal_link_is_not_positive_projection(self):
        _,(_,_,qs)=self.inventory('This will not lead to flooding.')
        self.assertEqual(qs,[])
    def test_binding_rejects_meta_even_if_model_requests_it(self):
        from faceted_source_v2 import bind_facets
        units,(ps,_,qs)=self.inventory("It's a thin line. Blocking users could silence critics.")
        self.assertTrue(qs)
        raw={'applications':[],'forecasts':{qs[0]['id']:dict(resolution='linked',initial_groups=[['p0']],stance='uses',reason='bad')}}
        with self.assertRaises(ValueError):bind_facets(raw,ps,units,qs)
