import copy
import unittest
from ontology_v2 import source_units
from warrants_v2 import validate_typing,apply_typing


class RoleGroundedTypingTests(unittest.TestCase):
    def setUp(self):
        self.units=source_units({'comment':'Our cultural heritage matters. We should preserve it.'})
        p=lambda unit,last:dict(unit=unit,first=0,last=last,owner='current_author',speech_act='assert',modality='certain',polarity='positive',event_role='none',implicit=False,gloss='')
        self.annotation={'propositions':[p(0,4),p(1,4)],'applications':[dict(kind='support',premises=[0],target_kind='proposition',target=1,scheme='other',stance='uses',scope_change='na',alternatives='na',roles=[],evidence=[dict(unit=0,first=0,last=4)])]}
        self.output={'annotations':{'a0':{'scheme':'historical_practice','scope_change':'na','alternatives':'na','roles':[{'role':'tradition','proposition':0},{'role':'claim','proposition':1}],'evidence':[dict(unit=0,first=0,last=4)],'reason':'Cultural tradition functions as a basis for preservation.'}}}

    def test_role_grounded_type_preserves_actual_direction(self):
        validate_typing(self.output,self.annotation,self.units)
        result=apply_typing(self.annotation,self.output)
        self.assertEqual(result['applications'][0]['scheme'],'historical_practice')
        self.assertEqual(result['applications'][0]['premises'],[0])
        self.assertEqual(result['applications'][0]['target'],1)
        self.assertEqual(self.annotation['applications'][0]['scheme'],'other')

    def test_testimony_requires_actual_source_and_claim_roles(self):
        out=copy.deepcopy(self.output);out['annotations']['a0'].update(scheme='testimony',roles=[])
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)

    def test_typing_cannot_sneak_in_reversed_endpoints(self):
        out=copy.deepcopy(self.output);out['annotations']['a0']['premises']=[1]
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)

    def test_unknown_scheme_keeps_the_source_application(self):
        out=copy.deepcopy(self.output);out['annotations']['a0'].update(scheme='other',roles=[])
        result=apply_typing(self.annotation,out)
        self.assertEqual(len(result['applications']),1)
        self.assertEqual(result['applications'][0]['premises'],[0])

    def test_wrong_claim_role_cannot_validate_a_typed_support(self):
        out=copy.deepcopy(self.output);out['annotations']['a0']['roles'][1]['proposition']=0
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)

    def test_tradition_from_unrelated_proposition_cannot_type_this_application(self):
        annotation=copy.deepcopy(self.annotation)
        # The target is not a reason offered by this application.
        out=copy.deepcopy(self.output);out['annotations']['a0']['roles'][0]['proposition']=1
        with self.assertRaises(ValueError):validate_typing(out,annotation,self.units)

    def test_claim_role_cannot_include_other_propositions_alongside_real_target(self):
        out=copy.deepcopy(self.output);out['annotations']['a0']['roles'].append({'role':'claim','proposition':0})
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)

    def test_role_specific_literal_subspan_of_premise_remains_usable(self):
        annotation=copy.deepcopy(self.annotation)
        subspan=copy.deepcopy(annotation['propositions'][0]);subspan.update(first=1,last=3)
        annotation['propositions'].append(subspan)
        out=copy.deepcopy(self.output);out['annotations']['a0']['roles'][0]['proposition']=2
        validate_typing(out,annotation,self.units)

    def test_choice_support_cannot_be_typed_as_priority_without_preference_act(self):
        out=copy.deepcopy(self.output);out['annotations']['a0'].update(scheme='priority_comparison',roles=[dict(role='preferred',proposition=0),dict(role='deprioritized',proposition=1),dict(role='criterion',proposition=0)])
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)

    def test_causal_warrant_requires_an_existing_projected_outcome(self):
        out=copy.deepcopy(self.output);out['annotations']['a0'].update(scheme='causal_projection',roles=[dict(role='initial',proposition=0),dict(role='consequence',proposition=1)])
        with self.assertRaises(ValueError):validate_typing(out,self.annotation,self.units)
