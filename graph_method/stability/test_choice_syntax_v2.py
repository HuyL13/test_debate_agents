import importlib.util
import json
import unittest
from pathlib import Path
from ontology_v2 import source_units

@unittest.skipUnless(importlib.util.find_spec('spacy') and importlib.util.find_spec('en_core_web_sm'), 'requires pinned syntax environment')
class ChoiceSyntaxTests(unittest.TestCase):
    def frames(self,text):
        from choice_syntax_v2 import choice_frames
        sample={'comment':text,'title':'','parent_comment':''}
        units=source_units(sample)
        frames=choice_frames(sample,units)
        for f in frames:
            for s in [f['scope']]+f['options']+f['closure_cues']+f['rejection_cues']:
                u=next(u for u in units if u['id']==s['unit'])
                a=u['tokens'][s['first']]['start']-u['start']; b=u['tokens'][s['last']-1]['end']-u['start']
                self.assertEqual(u['text'][a:b],s['text'])
        return frames
    def test_actual_clauses_and_negation(self):
        f=self.frames('You can either let the government do the right thing, or the country falls apart. There is few choices. This or nothing is the choice.')[0]
        self.assertIn('let the government do the right thing',f['options'][0]['text'])
        self.assertIn('country falls apart',f['options'][1]['text'])
        self.assertTrue(f['closure_cues']); self.assertFalse(f['rejection_cues'])
        f=self.frames('Either we do not intervene or we withdraw.')[0]
        self.assertIn('not intervene',f['options'][0]['text'])
    def test_open_list_vs_restriction(self):
        self.assertFalse(self.frames('We can walk or cycle.')[0]['closure_cues'])
        self.assertTrue(self.frames('Our only options are walking or cycling.')[0]['closure_cues'])
    def test_contrast_is_not_choice(self):
        self.assertEqual(self.frames('Tradition matters, but modern medicine helps people.'),[])
    def test_exposed_sources(self):
        samples=json.loads(Path('v2_critical_source_manifest.json').read_text(encoding='utf-8'))['samples']
        selected={s['sample_id']:s for s in samples if s['sample_id'] in ['35:3103','241:4919','524:10868']}
        frames=self.frames(selected['35:3103']['comment'])
        binary=next(f for f in frames if any('suffering' in o['text'] for o in f['options']))
        self.assertTrue(binary['rejection_cues'])
        extras=' '.join(o['text'] for f in frames for o in f['options'] if f is not binary)
        for word in ['mediation','international','solidarity']:self.assertIn(word,extras)
        self.assertEqual(self.frames(selected['524:10868']['comment']),[])
