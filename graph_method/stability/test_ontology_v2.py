import copy
import unittest
from ontology_v2 import *

class OntologyTests(unittest.TestCase):
    def setUp(self):
        self.units=source_units({'comment':'If we block users critics might vanish. Protect speech.', 'parent_comment':'Trust tradition.'})
        self.p=lambda unit,first,last,**kw: dict(unit=unit,first=first,last=last,owner='current_author',speech_act='assert',modality='possible',polarity='positive',event_role='none',implicit=False,gloss='',**kw)
    def prop(self,unit,first,last,**kw):
        p=self.p(unit,first,last);p.update(kw);return p
    def app(self,**kw):
        a=dict(kind='support',premises=[0],target_kind='proposition',target=1,scheme='other',stance='uses',scope_change='na',alternatives='na',evidence=[dict(unit=0,first=0,last=7)],roles=[]);a.update(kw);return a
    def annotation(self):
        return dict(propositions=[self.prop(0,0,4,event_role='condition',speech_act='hypothetical'),self.prop(0,4,7,event_role='outcome',speech_act='hypothetical')],applications=[self.app(kind='projection')])
    def test_exact_within_unit(self):
        a=self.annotation();s=proposition_span(a['propositions'][1],self.units)
        self.assertEqual(s['text'],'critics might vanish.');self.assertEqual(s['start'],18)
        g=compile_graph(a,self.units);self.assertEqual(sum(n['type']=='EventMention' for n in g['nodes']),2)
        self.assertIn('PROJECTED_NEXT',{e['type'] for e in g['edges']})
    def test_bounds_and_exact_fields(self):
        for change in [{'last':99},{'first':True},{'first':4,'last':4},{'text':'invented'}]:
            a=self.annotation();a['propositions'][0].update(change)
            with self.assertRaises(ValueError):validate_annotation(a,self.units)
    def test_wrong_event_target(self):
        for change in [{'speech_act':'recommend'},{'speech_act':'meta'},{'event_role':'none'}]:
            a=self.annotation();a['propositions'][1].update(change)
            with self.assertRaises(ValueError):validate_annotation(a,self.units)
    def test_recommended_action_can_antecede_outcome(self):
        a=self.annotation();a['propositions'][0].update(speech_act='recommend',event_role='action')
        g=compile_graph(a,self.units)
        self.assertTrue(any(n['id']=='event0' for n in g['nodes']))
        a['propositions'][0]['speech_act']='meta'
        a['applications']=[]
        with self.assertRaises(ValueError):validate_annotation(a,self.units)
    def test_context_premise_requires_explicit_adoption(self):
        units,a,adoption=self.adoption_fixture()
        with self.assertRaises(ValueError):validate_annotation(a,units)
        a['applications'].append(adoption)
        validate_annotation(a,units)
    def test_parent_ownership(self):
        a=dict(propositions=[self.prop(2,0,2)],applications=[])
        with self.assertRaises(ValueError):validate_annotation(a,self.units)
        a['propositions'][0]['owner']='parent_author';validate_annotation(a,self.units)
    def test_undercut_and_cycles(self):
        a=self.annotation();a['applications'].append(self.app(kind='undercut',target_kind='application',target=0));validate_annotation(a,self.units)
        a['applications'][0].update(kind='support',target_kind='application',target=1)
        with self.assertRaises(ValueError):validate_annotation(a,self.units)
        a=self.annotation();a['applications'][0]['kind']='undercut'
        with self.assertRaises(ValueError):validate_annotation(a,self.units)
    def test_implicit_and_unknown(self):
        a=self.annotation();a['propositions'][1].update(implicit=True,gloss='A hypothesized loss');g=compile_graph(a,self.units)
        self.assertTrue(next(n for n in g['nodes'] if n['id']=='assertion1')['hypothesized'])
        self.assertEqual(next(n for n in g['nodes'] if n['id']=='p1')['content'],'A hypothesized loss')
        self.assertEqual(len([n for n in g['nodes'] if n['type']=='SchemeHypothesis']),1)
    def test_preference_roles(self):
        a=self.annotation();a['applications'][0]['kind']='preference'
        with self.assertRaises(ValueError):validate_annotation(a,self.units)
        a['applications'][0]['roles']=[dict(role='preferred',proposition=0),dict(role='deprioritized',proposition=1)];validate_annotation(a,self.units)
    def test_payload_schema(self):
        payload=source_payload({'comment':'hi','gold':'secret'},self.units);self.assertNotIn('gold',str(payload))
        schema=annotation_schema(self.units);self.assertFalse(schema['additionalProperties']);self.assertEqual(schema['properties']['propositions']['maxItems'],48)
    def test_adoption_keeps_context_separate(self):
        units,a,adoption=self.adoption_fixture();a['applications']=[adoption]
        g=compile_graph(a,units)
        self.assertIn('ADOPTS',{e['type'] for e in g['edges']})
        a['applications'][0]['evidence']=[dict(unit=2,first=0,last=2)]
        with self.assertRaises(ValueError):validate_annotation(a,units)
    def test_self_target_duplicates_and_bad_roles(self):
        for changes in [dict(target=0),dict(premises=[0,0]),dict(roles=[dict(role='source',proposition=99)])]:
            a=self.annotation();a['applications'][0].update(changes)
            with self.assertRaises(ValueError):validate_annotation(a,self.units)
    def test_warrant_support_and_overlaps_are_preserved(self):
        a=self.annotation();a['propositions'].append(self.prop(0,0,7))
        a['applications'].append(self.app(premises=[2],target_kind='application',target=0))
        g=compile_graph(a,self.units)
        self.assertEqual(len([n for n in g['nodes'] if n['type']=='Proposition']),3)
        self.assertTrue(any(e['type']=='TARGETS' and e['target']=='a0' for e in g['edges']))

    def test_concession_is_discourse_content_not_a_supporting_premise(self):
        a=self.annotation();a['applications'][0].update(kind='concession',scheme='other',roles=[])
        g=compile_graph(a,self.units)
        self.assertTrue(any(n['id']=='a0' and n['type']=='DiscourseApplication' for n in g['nodes']))
        self.assertTrue(any(e['target']=='a0' and e['type']=='CONCEDED_CONTENT' for e in g['edges']))
        self.assertFalse(any(e['target']=='a0' and e['type']=='PREMISE_OF' for e in g['edges']))

    def test_concession_cannot_be_promoted_to_an_argumentative_scheme(self):
        a=self.annotation();a['applications'][0].update(kind='concession',scheme='historical_practice')
        with self.assertRaises(ValueError):validate_annotation(a,self.units)

    def adoption_fixture(self):
        units=source_units(dict(comment="Yes, that's right. Keep debate open.",parent_comment='We must protect speech.'))
        ps=[self.prop(0,0,3),self.prop(1,0,3,speech_act='recommend'),self.prop(2,0,4,owner='parent_author',speech_act='recommend')]
        support=self.app(premises=[2],target=1,evidence=[dict(unit=1,first=0,last=3)])
        adoption=self.app(kind='adoption',premises=[0],target=2,roles=[dict(role='adoption_cue',proposition=0)],evidence=[dict(unit=0,first=0,last=3)])
        return units,dict(propositions=ps,applications=[support]),adoption

    def test_context_adoption_needs_an_actual_positive_endorsement_in_comment(self):
        a=self.annotation();a['propositions'].append(self.prop(2,0,2,owner='parent_author'))
        a['applications']=[self.app(kind='adoption',target=2,roles=[dict(role='adoption_cue',proposition=0)])]
        with self.assertRaisesRegex(ValueError,'endorsement'):validate_annotation(a,self.units)

    def test_negated_agreement_cannot_license_context_adoption(self):
        units=source_units(dict(comment='I do not agree.',parent_comment='Trust tradition.'))
        a=dict(propositions=[self.prop(0,0,4,polarity='negative'),self.prop(1,0,2,owner='parent_author')],applications=[self.app(kind='adoption',target=1,roles=[dict(role='adoption_cue',proposition=0)],evidence=[dict(unit=0,first=0,last=4)])])
        with self.assertRaisesRegex(ValueError,'endorsement'):validate_annotation(a,units)

    def test_endorsement_license_does_not_confuse_adjectives_or_negation(self):
        for text in ['We cannot trust it to report correct information.',"I do not think you're right.",'It is a tragic situation indeed.']:
            self.assertFalse(has_positive_endorsement(text),text)
        for text in ["I couldn't agree more.",'Yes, that is right.','I agree with the negative assessment.']:
            self.assertTrue(has_positive_endorsement(text),text)

    def test_adoption_reference_cannot_become_a_warrant(self):
        units,a,adoption=self.adoption_fixture();a['applications']=[adoption]
        adoption['scheme']='historical_practice'
        with self.assertRaises(ValueError):validate_annotation(a,units)

if __name__=='__main__':unittest.main()
