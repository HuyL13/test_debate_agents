import unittest
from copy import deepcopy
from graph_guard import compile_guarded, hypotheses, source_obligations

class GraphGuardTests(unittest.TestCase):
    def test_typed_projection_checks_scenario_not_reason_to_target(self):
        row=self.row();row['extraction']['arguments'][0].update(operator='causal_projection',chain=[0,1])
        questions=dict(hypotheses(row,typed=True))
        self.assertIn('projected consequence',questions['a0_binding'])
        self.assertNotIn('reason-to-target',questions['a0_binding'])

    def test_direct_transition_has_one_authoritative_source_obligation(self):
        row=self.row();row['extraction']['arguments'][0].update(operator='causal_projection',chain=[0,1])
        questions=dict(hypotheses(row,typed=True))
        self.assertEqual(questions['a0_binding'],questions['a0_chain0'])
        self.assertEqual(questions['a0_scheme'],questions['a0_chain0'])
        plan=source_obligations(row,typed=True)
        shared=[p for p in plan if p[0]=='a0_chain0']
        self.assertEqual(len(shared),1)
        self.assertEqual(set(shared[0][2]),{'a0_binding','a0_scheme','a0_chain0'})
        self.assertEqual(len(plan),2)

    def test_internal_causal_chain_does_not_turn_support_target_into_event(self):
        row=self.row();row['extraction']['arguments'][0].update(operator='causal_projection',premises=[0,1],conclusion=2,chain=[0,1])
        questions=dict(hypotheses(row,typed=True))
        self.assertIn('reason-to-target',questions['a0_binding'])
        self.assertNotIn('target consequence',questions['a0_scheme'])

    def test_conflicting_equivalent_source_checks_are_quarantined(self):
        row=self.row();row['extraction']['arguments'][0].update(operator='causal_projection',chain=[0,1])
        answers=self.answers();answers['a0_binding']['verdict']='unsupported'
        result=compile_guarded(row,answers,typed=True)
        self.assertEqual(result['extraction']['arguments'],[])
        self.assertEqual(len(result['verification_conflicts']),1)
        self.assertEqual(result['verification_conflicts'][0]['argument_index'],0)
        self.assertIn('a0_chain0',result['verification_conflicts'][0]['checks'])

    def test_scheme_rejection_alone_is_not_binding_conflict(self):
        answers=self.answers();answers['a0_scheme']['verdict']='unsupported'
        result=compile_guarded(self.row(),answers,typed=True)
        self.assertEqual(result['verification_conflicts'],[])
        self.assertEqual(result['extraction']['arguments'][0]['operator'],'other')
    def row(self):
        return {'units':[{'id':0,'source':'comment','text':'The company wants profit.','start':0,'end':25},{'id':1,'source':'comment','text':'Why worry?','start':26,'end':36}], 'extraction':{'arguments':[{'premises':[0],'conclusion':1,'operator':'testimony','stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[]}]}}
    def answers(self):return {key:{'status':'accepted','verdict':'supported','call_id':key} for key in ['a0_binding','a0_scheme','a0_commitment','a0_chain0']}
    def test_unsupported_scheme_does_not_destroy_supported_relation(self):
        row=self.row();before=deepcopy(row);answers=self.answers();answers['a0_scheme']['verdict']='unsupported'
        result=compile_guarded(row,answers)
        self.assertEqual(result['extraction']['arguments'][0]['operator'],'other')
        self.assertEqual(result['extraction']['arguments'][0]['premises'],[0])
        self.assertEqual(row,before)
    def test_rejected_binding_is_not_committed(self):
        answers=self.answers();answers['a0_binding']['verdict']='unsupported'
        result=compile_guarded(self.row(),answers)
        self.assertEqual(result['extraction']['arguments'],[])
        self.assertEqual(result['uncommitted_argument_indices'],[0])
    def test_invalid_event_chain_removed_without_inventing_bridge(self):
        row=self.row();row['extraction']['arguments'][0].update(operator='causal_projection',chain=[0,1])
        answers=self.answers();answers['a0_chain0']['verdict']='unsupported'
        result=compile_guarded(row,answers)
        self.assertEqual(result['extraction']['arguments'][0]['chain'],[])
        self.assertFalse(any(e['rel']=='PROJECTED_NEXT' for e in result['graph']['edges']))

    def test_collapsed_unknown_schemes_preserve_both_proposal_origins(self):
        row=self.row();row['extraction']['arguments'].append(dict(row['extraction']['arguments'][0],operator='evidence'))
        answers=self.answers();answers.update({'a1_binding':answers['a0_binding'],'a1_scheme':{'status':'accepted','verdict':'unsupported'},'a1_commitment':answers['a0_commitment']});answers['a0_scheme']['verdict']='unsupported'
        result=compile_guarded(row,answers)
        self.assertEqual(len(result['extraction']['arguments']),1)
        self.assertEqual(result['argument_provenance'][0]['proposal_argument_indices'],[0,1])
