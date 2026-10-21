import copy
import unittest
from ontology_v2 import source_units,proposition_span
from source_quotes_v2 import annotation_from_quotes


class QuotedSourceAlignmentTests(unittest.TestCase):
    def test_glued_sentences_and_clause_dashes_keep_exact_offsets(self):
        from source_quotes_v2 import _anchor
        cases=[('humans.Unnecessary killing','humans.'),('humans.Unnecessary killing','Unnecessary killing'),('dangerous precedent-once liberties crumble','once liberties crumble'),('the world--or democracy diminishes','the world'),('rights--then government decides','then government decides')]
        for text,quote in cases:
            units=source_units({'comment':text})
            anchor=_anchor(dict(unit=0,quote=quote,occurrence=0),units)
            span=proposition_span(anchor,units)
            self.assertIn(quote,span['text'])
            self.assertEqual(text[span['start']:span['end']],span['text'])
    def test_negation_and_compound_word_clipping_stays_rejected(self):
        from source_quotes_v2 import _anchor
        for text,quote in [("can't act",'can'),('non-dangerous snakes','dangerous snakes'),('unnecessary killing','necessary killing')]:
            with self.assertRaises(ValueError):_anchor(dict(unit=0,quote=quote,occurrence=0),source_units({'comment':text}))
    def setUp(self):
        self.units=source_units({'comment':"If we can't block users critics might vanish. Protect speech."})
        def p(id,quote,**kw):
            out=dict(id=id,unit=0,quote=quote,occurrence=0,owner='current_author',speech_act='hypothetical',modality='possible',polarity='positive',event_role='none',implicit=False,gloss='');out.update(kw);return out
        self.raw={'propositions':[p('p9',"If we can't block users",event_role='condition'),p('p2','critics might vanish',event_role='outcome')],
            'applications':[dict(id='a7',kind='projection',premises=['p9'],target_kind='proposition',target='p2',scheme='other',stance='uses',scope_change='na',alternatives='na',evidence=[dict(unit=0,quote='critics might vanish',occurrence=0)],roles=[dict(role='initial',proposition='p9'),dict(role='consequence',proposition='p2')])]}

    def test_explicit_ids_and_quotes_determine_actual_direction(self):
        a=annotation_from_quotes(self.raw,self.units)
        self.assertEqual(len(a['propositions']),2)
        self.assertEqual(proposition_span(a['propositions'][1],self.units)['text'],'critics might vanish.')
        self.assertEqual(a['applications'][0]['premises'],[0])
        self.assertEqual(a['applications'][0]['target'],1)
        reversed_order=copy.deepcopy(self.raw);reversed_order['propositions'].reverse()
        b=annotation_from_quotes(reversed_order,self.units)
        self.assertEqual(b['applications'][0]['premises'],[1])
        self.assertEqual(b['applications'][0]['target'],0)

    def test_invented_or_midword_quote_is_rejected(self):
        for quote in ['people must disappear', 'can']:
            raw=copy.deepcopy(self.raw);raw['propositions'][0]['quote']=quote
            with self.assertRaises(ValueError):annotation_from_quotes(raw,self.units)

    def test_ambiguous_repeated_quote_uses_explicit_occurrence(self):
        units=source_units({'comment':'fear causes fear.'})
        raw=copy.deepcopy(self.raw);raw['applications']=[];raw['propositions']=raw['propositions'][:1]
        raw['propositions'][0].update(quote='fear',occurrence=1,event_role='none')
        a=annotation_from_quotes(raw,units)
        self.assertEqual(len(a['propositions']),1)
        self.assertEqual(proposition_span(a['propositions'][0],units)['text'],'fear.')

    def test_whitespace_normalization_preserves_original_source(self):
        units=source_units({'comment':'critics   might vanish.'})
        raw=copy.deepcopy(self.raw);raw['applications']=[];raw['propositions']=raw['propositions'][1:]
        a=annotation_from_quotes(raw,units)
        self.assertEqual(proposition_span(a['propositions'][0],units)['text'],'critics   might vanish.')

    def test_role_extra_fields_are_rejected(self):
        raw=copy.deepcopy(self.raw);raw['applications'][0]['roles'][0]['invented']='value'
        with self.assertRaises(ValueError):annotation_from_quotes(raw,self.units)

    def test_failed_quote_reports_literal_and_original_unit_for_repair(self):
        raw=copy.deepcopy(self.raw);raw['propositions'][0]['quote']='invented wording'
        with self.assertRaises(ValueError) as caught:annotation_from_quotes(raw,self.units)
        message=str(caught.exception)
        self.assertIn('invented wording',message)
        self.assertIn("can't block users",message)

    def test_invalid_endpoint_cannot_be_repaired_to_a_different_id(self):
        raw=copy.deepcopy(self.raw);raw['applications'][0]['target']='p1'
        with self.assertRaises(ValueError):annotation_from_quotes(raw,self.units)
