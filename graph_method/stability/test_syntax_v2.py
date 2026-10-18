import importlib.util
import unittest
from syntax_v2 import analyse_text

@unittest.skipUnless(importlib.util.find_spec('spacy'),'run with .venv-syntax/Scripts/python.exe')
class SyntaxSemanticProfiles(unittest.TestCase):
    def test_metacomment_is_not_an_initial_event(self):
        p=analyse_text("It's really a thin line on what should be allowed and what shouldn't be allow on social media and who it comes from.")
        self.assertEqual(p['content_kind'],'metacomment')
        self.assertFalse(p['initial_eligible']);self.assertFalse(p['outcome_eligible'])
    def test_permission_question_is_a_possible_initial_action(self):
        p=analyse_text("shouldn't they be allowed to block that user?")
        self.assertTrue(p['initial_eligible']);self.assertFalse(p['outcome_eligible'])
        self.assertIn('block',p['action_predicates'])
    def test_recommendation_is_not_a_predicted_outcome(self):
        p=analyse_text('We need to make sure freedom of speech is preserved while ensuring no one is insulted.')
        self.assertEqual(p['content_kind'],'normative_action');self.assertFalse(p['outcome_eligible'])
    def test_epistemic_conclusion_is_not_a_world_event(self):
        p=analyse_text('We cannot trust the agency to report correct information, if a victim was charged.')
        self.assertEqual(p['content_kind'],'epistemic_evaluation');self.assertFalse(p['outcome_eligible'])
    def test_conditional_approval_is_not_an_event_outcome(self):
        for text in ['If they want to return them, great.','If they want to return them, fine.']:
            p=analyse_text(text);self.assertFalse(p['outcome_eligible'])
    def test_projected_effect_is_anchored_and_preserves_modality(self):
        text='This might lead to a politician blocking anyone who voices criticism.'
        p=analyse_text(text)
        self.assertTrue(p['outcome_eligible']);self.assertTrue(p['forecast'])
        self.assertEqual(p['modality'],'possible')
        effect=p['effect_span'];self.assertEqual(text[effect['start']:effect['end']],effect['text'])
        self.assertIn('blocking',effect['text']);self.assertEqual(p['effect_predicate'],'block')
    def test_world_event_conditional_preserves_cause_and_effect(self):
        text='If the river rises, nearby homes will flood.'
        p=analyse_text(text);self.assertTrue(p['forecast']);self.assertTrue(p['outcome_eligible'])
        self.assertEqual(p['predicate']['lemma'],'flood')
        self.assertIn('river',p['condition_spans'][0]['text'])
