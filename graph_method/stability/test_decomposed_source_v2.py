"""Tests for two-stage source anchoring and endpoint binding."""
import copy
import unittest
from ontology_v2 import source_units,proposition_span
from decomposed_source_v2 import prepare_propositions,bind_relations,relation_schema,process

class DecomposedSourceTests(unittest.TestCase):
    def test_nonempty_comment_cannot_be_repaired_into_empty_propositions(self):
        with self.assertRaises(ValueError):prepare_propositions({'propositions':[]},source_units({'comment':'The rule harms people.'}))
    def setUp(self):
        self.units=source_units({'comment':'Permit blocking. Critics might be silenced.'})
        def p(unit,quote,act):return dict(unit=unit,quote=quote,owner='current_author',speech_act=act,modality='possible',polarity='positive',event_role='none',implicit=False,gloss='')
        self.raw={'propositions':[p(0,'Permit blocking.','recommend'),p(1,'Critics might be silenced.','hypothetical')]}
        self.ps=prepare_propositions(self.raw,self.units)
        self.links={'applications':[dict(id='a0',kind='projection',premises=['p0'],target_kind='proposition',target='p1',stance='uses',roles=[dict(role='initial',proposition='p0'),dict(role='consequence',proposition='p1')],evidence_units=[1])]}
    def test_code_assigns_ids_and_binds_projection_without_rewriting_source(self):
        a=bind_relations(self.links,self.ps,self.units)
        self.assertEqual(a['applications'][0]['premises'],[0]);self.assertEqual(a['applications'][0]['target'],1)
        self.assertEqual(proposition_span(a['propositions'][1],self.units)['text'],'Critics might be silenced.')
        self.assertEqual(a['propositions'][0]['speech_act'],'recommend')
    def test_relation_stage_cannot_replace_literal_propositions(self):
        raw=copy.deepcopy(self.links);raw['propositions']=[]
        with self.assertRaises(ValueError):bind_relations(raw,self.ps,self.units)
    def test_event_binding_cannot_create_recommendation_as_harmful_outcome(self):
        raw=copy.deepcopy(self.links);raw['applications'][0].update(premises=['p1'],target='p0')
        with self.assertRaises(ValueError):bind_relations(raw,self.ps,self.units)
    def test_projection_event_roles_are_derived_from_directed_binding(self):
        a=bind_relations(self.links,self.ps,self.units)
        self.assertEqual(a['propositions'][0]['event_role'],'action')
        self.assertEqual(a['propositions'][1]['event_role'],'outcome')

    def test_model_cannot_supply_redundant_global_event_role_table(self):
        raw=copy.deepcopy(self.links);raw['event_roles']={'p0':'none','p1':'none'}
        with self.assertRaises(ValueError):bind_relations(raw,self.ps,self.units)

    def test_evidence_unit_is_code_owned_and_must_exist(self):
        raw=copy.deepcopy(self.links);raw['applications'][0]['evidence_units']=[999]
        with self.assertRaises(ValueError):bind_relations(raw,self.ps,self.units)
    def test_relation_schema_only_allows_actual_propositions(self):
        schema=relation_schema(self.ps,self.units)
        branches=schema['properties']['applications']['items']['anyOf']
        for branch in branches:self.assertEqual(branch['properties']['premises']['items']['enum'],['p0','p1'])

    def test_full_process_keeps_stage_outputs_and_never_sends_gold(self):
        inputs=[]
        def fake(model,stage,sid,system,payload,validator,version,repeat,settings):
            inputs.append((stage,payload))
            if stage=='source_propositions_v2':out=self.raw
            elif stage=='source_relations_v2':out=self.links
            else:out={'annotations':{'a0':dict(scheme='causal_projection',scope_change='na',alternatives='na',roles=[dict(role='initial',proposition=0),dict(role='consequence',proposition=1)],evidence=[dict(unit=1,first=0,last=4)],reason='A blocking policy is offered as the condition for a possible silencing outcome.')}}
            validator(out)
            return dict(status='accepted',call_id=stage,output=copy.deepcopy(out))
        sample=dict(sample_id='fixture',article_id=1,split='induction',gold='PRIVATE_LABEL',comment='Permit blocking. Critics might be silenced.')
        row=process(sample,invoke_fn=fake)
        self.assertEqual(row['status'],'accepted');self.assertEqual(len(inputs),3)
        self.assertNotIn('PRIVATE_LABEL',str(inputs))
        self.assertNotIn('applications',inputs[1][1])
        self.assertEqual(row['annotation']['applications'][0]['scheme'],'causal_projection')
        self.assertEqual(row['annotation']['propositions'][0]['speech_act'],'recommend')
        self.assertEqual(row['proposal_annotation']['applications'],[])

    def test_failed_relation_stage_cannot_publish_propositions_as_accepted_graph(self):
        def fake(model,stage,sid,system,payload,validator,version,repeat,settings):
            if stage=='source_propositions_v2':return dict(status='accepted',call_id=stage,output=copy.deepcopy(self.raw))
            return dict(status='quality_rejected',call_id=stage,output=None)
        row=process(dict(sample_id='fixture',comment='Permit blocking. Critics might be silenced.'),invoke_fn=fake)
        self.assertEqual(row['status'],'witness_failed');self.assertIsNone(row['annotation']);self.assertIsNone(row['graph'])

    def test_repeated_ambiguous_quote_requires_distinguishing_context(self):
        units=source_units({'comment':'fear causes fear.'})
        raw=copy.deepcopy(self.raw);raw['propositions']=raw['propositions'][:1];raw['propositions'][0].update(unit=0,quote='fear')
        with self.assertRaises(ValueError):prepare_propositions(raw,units)

    def test_model_cannot_supply_occurrence_or_code_owned_id(self):
        for extra in [{'occurrence':86},{'id':'p86'}]:
            raw=copy.deepcopy(self.raw);raw['propositions'][0].update(extra)
            with self.assertRaises(ValueError):prepare_propositions(raw,self.units)

    def test_no_endorsement_blocks_author_use_of_context_at_schema_boundary(self):
        units=source_units(dict(comment='The conclusion is wrong.',parent_comment='Most agree.'))
        raw=copy.deepcopy(self.raw)
        raw['propositions'][0].update(unit=0,quote='The conclusion is wrong.',speech_act='assert')
        raw['propositions'][1].update(unit=1,quote='Most agree.',owner='parent_author',speech_act='assert')
        ps=prepare_propositions(raw,units)
        branches=relation_schema(ps,units)['properties']['applications']['items']['anyOf']
        uses=next(b['properties'] for b in branches if b['properties']['stance']['enum']==['uses'])
        self.assertEqual(uses['premises']['items']['enum'],['p0'])
        self.assertNotIn('adoption',uses['kind']['enum'])
        reported=next(b['properties'] for b in branches if 'reports' in b['properties']['stance']['enum'])
        self.assertEqual(reported['premises']['items']['enum'],['p0','p1'])

    def test_actual_endorsement_enables_only_grounded_adoption_slots(self):
        units=source_units(dict(comment="Yes, that's right.",parent_comment='It is harmful.'))
        raw=copy.deepcopy(self.raw)
        raw['propositions'][0].update(unit=0,quote="Yes, that's right.",speech_act='assert')
        raw['propositions'][1].update(unit=1,quote='It is harmful.',owner='parent_author',speech_act='assert')
        ps=prepare_propositions(raw,units)
        branches=relation_schema(ps,units)['properties']['applications']['items']['anyOf']
        adoption=next(b['properties'] for b in branches if b['properties']['kind']['enum']==['adoption'])
        self.assertEqual(adoption['premises']['items']['enum'],['p0'])
        self.assertEqual(adoption['target']['enum'],['p1'])
        self.assertEqual(adoption['roles']['items']['properties']['role']['enum'],['adoption_cue'])
