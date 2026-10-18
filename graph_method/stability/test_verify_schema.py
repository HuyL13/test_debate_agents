import unittest
from verifier_structured import canonicalize,verification_schema


class VerifierSchemaTests(unittest.TestCase):
    def test_every_candidate_has_fixed_object_key(self):
        schema=verification_schema([{'id':'c0'},{'id':'c1'}],[{'id':0},{'id':1}])
        self.assertEqual(set(schema['properties']['assessments']['required']),{'c0','c1'})
        self.assertFalse(schema['properties']['assessments']['additionalProperties'])

    def test_canonicalization_preserves_source_checks(self):
        raw={'assessments':{'c0':{'mapping_status':'valid','mechanism':'present','author':'endorsed','defect':'supported','reason_code':'warrant_misuse','centrality':'central','evidence':[0,1],'reason':'Grounded reason.'}}}
        out=canonicalize(raw)
        self.assertEqual(out['assessments'][0]['candidate_id'],'c0')
        self.assertEqual(out['assessments'][0]['mapping_status'],'valid')


if __name__=='__main__':unittest.main()
