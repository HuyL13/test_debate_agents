import unittest
from staged_roles import validate_roles,validate_schemes,compile_result

class StagedTests(unittest.TestCase):
    units=[{'id':0,'source':'comment','text':'Most believe it.','start':0,'end':16},{'id':1,'source':'comment','text':'It is true.','start':17,'end':28}]
    roles={'moves':[{'premises':[0],'conclusion':1,'stance':'uses','description':'Popularity supports truth.'}]}
    def assessment(self):return {'mapping_status':'valid','operator':'consensus','stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[],'escalation':'na','reason':'The belief of many supports the truth claim.'}
    def test_self_premise_rejected(self):
        with self.assertRaises(ValueError):validate_roles({'moves':[dict(self.roles['moves'][0],premises=[1])]},self.units)
    def test_every_fixed_move_must_be_assessed(self):
        with self.assertRaises(ValueError):validate_schemes({'moves':{}},self.roles,self.units)
    def test_compiler_cannot_silently_change_mapping(self):
        out=compile_result(self.roles,{'moves':{'m0':self.assessment()}},self.units)
        self.assertEqual(out['extraction']['arguments'][0]['premises'],[0])
        self.assertEqual(out['extraction']['arguments'][0]['conclusion'],1)
        invalid=dict(self.assessment(),mapping_status='invalid')
        self.assertEqual(compile_result(self.roles,{'moves':{'m0':invalid}},self.units)['extraction']['arguments'],[])
