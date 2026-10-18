import copy
import unittest
from unittest.mock import patch
from source_quotes_v2 import annotation_to_quotes
from ontology_v2 import source_units
from pipeline_v2 import process,compare_annotations


class DirectedWitnessPipelineTests(unittest.TestCase):
    def setUp(self):
        self.sample={'sample_id':'fixture','article_id':1,'gold':'PRIVATE_LABEL','comment':'Heritage matters, so protect it.'}
        self.units=source_units(self.sample)
        def prop(unit,last):
            return dict(unit=unit,first=0,last=last,owner='current_author',speech_act='assert',modality='certain',polarity='positive',event_role='none',implicit=False,gloss='')
        self.forward={'propositions':[prop(0,2),prop(1,3)],'applications':[dict(kind='support',premises=[0],target_kind='proposition',target=1,scheme='evidence',stance='uses',scope_change='na',alternatives='na',evidence=[dict(unit=0,first=0,last=2),dict(unit=1,first=0,last=3)],roles=[])]}
        self.reverse=copy.deepcopy(self.forward);self.reverse['applications'][0].update(premises=[1],target=0)

    def fake_invoke(self,proposal,witness,witness_status='accepted',proposal_status='accepted',typing_status='accepted'):
        self.inputs=[]
        def fake(model,stage,sid,system,user,validator,version,repeat,settings):
            self.inputs.append((stage,user))
            if stage=='warrant_roles_v2':
                output={'annotations':{'a'+str(i):{'scheme':a['scheme'],'scope_change':a['scope_change'],'alternatives':a['alternatives'],'roles':a['roles'],'evidence':a['evidence'],'reason':'Literal source-grounded ordinary support.'} for i,a in enumerate(witness['applications'])}}
                if typing_status=='accepted':validator(output)
                return {'status':typing_status,'call_id':'typing','output':output if typing_status=='accepted' else None,'attempts':[]}
            is_witness=stage=='source_witness_v2'
            output=witness if is_witness else proposal
            status=witness_status if is_witness else proposal_status
            if status=='accepted':
                output=annotation_to_quotes(output,self.units)
                validator(output)
            return {'status':status,'call_id':'witness' if is_witness else 'proposal','output':copy.deepcopy(output) if status=='accepted' else None,'attempts':[]}
        return fake

    def test_failed_typing_preserves_relation_and_exposes_stage_failure(self):
        with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(self.forward,self.forward,typing_status='rejected')):
            row=process(self.sample)
        self.assertEqual(row['status'],'typing_failed')
        self.assertEqual(row['stage_status']['warrant'],'rejected')
        self.assertEqual(row['annotation']['applications'][0]['premises'],[0])
        self.assertEqual(row['annotation']['applications'][0]['scheme'],'other')

    def test_witness_direction_replaces_reversed_proposal(self):
        with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(self.reverse,self.forward)):
            row=process(self.sample)
        self.assertEqual(row['status'],'accepted')
        self.assertEqual(row['annotation']['applications'][0]['premises'],[0])
        self.assertEqual(row['annotation']['applications'][0]['target'],1)
        self.assertEqual(len(row['comparison']['proposal_only']),1)
        self.assertEqual(len(row['comparison']['witness_only']),1)

    def test_missing_proposal_link_is_recovered_from_source_witness(self):
        empty=copy.deepcopy(self.forward);empty['applications']=[]
        with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(empty,self.forward)):
            row=process(self.sample)
        self.assertEqual(row['status'],'accepted')
        self.assertEqual(len(row['annotation']['applications']),1)
        self.assertEqual(len(row['comparison']['witness_only']),1)

    def test_witness_never_receives_proposed_edges_or_gold(self):
        payloads=[]
        for proposal in [self.forward,self.reverse]:
            with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(proposal,self.forward)):
                row=process(self.sample)
            self.assertEqual(row['status'],'accepted')
            payloads.append(next(u for stage,u in self.inputs if stage=='source_witness_v2'))
        self.assertEqual(payloads[0],payloads[1])
        self.assertNotIn('PRIVATE_LABEL',str(payloads[0]))
        self.assertNotIn('applications',payloads[0])

    def test_failed_witness_does_not_silently_commit_proposal(self):
        with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(self.forward,self.forward,witness_status='infrastructure_error')):
            row=process(self.sample)
        self.assertEqual(row['status'],'witness_failed')
        self.assertIsNone(row['annotation'])
        self.assertEqual(row['proposal_annotation'],self.forward)

    def test_failed_proposal_is_visible_when_witness_recovers(self):
        with patch('pipeline_v2.invoke',side_effect=self.fake_invoke(None,self.forward,proposal_status='rejected')):
            row=process(self.sample)
        self.assertEqual(row['status'],'accepted')
        self.assertEqual(row['stage_status']['proposal'],'rejected')
        self.assertEqual(row['stage_status']['witness'],'accepted')

    def test_endpoint_comparison_does_not_confuse_reverse_with_agreement(self):
        result=compare_annotations(self.reverse,self.forward,self.units)
        self.assertEqual(result['confirmed'],[])
        self.assertEqual(len(result['proposal_only']),1)
        self.assertEqual(len(result['witness_only']),1)


if __name__=='__main__':unittest.main()
