import unittest
from unitization import split_units_v4


class UnitTests(unittest.TestCase):
    def test_quote_does_not_join_two_sentences(self):
        source={'comment':'They mock the new "leader." Nothing is more natural.','title':'','parent_comment':''}
        units=split_units_v4(source)
        self.assertEqual(len(units),2)
        self.assertEqual(units[1]['text'],'Nothing is more natural.')
        for u in units:self.assertEqual(source[u['source']][u['start']:u['end']],u['text'])

    def test_intra_sentence_inference_is_not_lost(self):
        source={'comment':'Failure at this task shows that they are bad at all tasks.','title':'','parent_comment':''}
        us=split_units_v4(source)
        self.assertEqual(len(us),2)
        self.assertIn('shows that',us[1]['text'])

    def test_because_can_follow_conclusion(self):
        us=split_units_v4({'comment':'We should keep it because it has lasted centuries.','title':'','parent_comment':''})
        self.assertEqual(len(us),2)
        self.assertEqual(us[0]['text'],'We should keep it')

    def test_projected_steps_have_individual_grounded_units(self):
        text='Groups will invade spaces, which will lead to injuries, which will lead to riots.'
        us=split_units_v4({'comment':text,'title':'','parent_comment':''})
        self.assertGreaterEqual(len(us),3)
        for u in us:self.assertEqual(text[u['start']:u['end']],u['text'])

    def test_connective_inside_verb_phrase_does_not_split_modality(self):
        from unitization import split_units_v5
        text='AI can therefore be affected by programmer biases.'
        self.assertEqual(len(split_units_v5({'comment':text})),1)

    def test_rhetorical_question_and_fragment_answer_remain_together(self):
        from unitization import split_units_v5
        text="What is more natural? For people to talk in person. We should do that."
        units=split_units_v5({'comment':text})
        self.assertEqual(len(units),2)
        self.assertIn('For people',units[0]['text'])


if __name__=='__main__':unittest.main()
