import unittest
from atomic_fidelity import validate_answer,answer_schema

class AtomicFidelityTests(unittest.TestCase):
    def test_known_truth_values_need_real_source_evidence(self):
        units=[{'id':0},{'id':1}]
        with self.assertRaises(ValueError):validate_answer({'verdict':'supported','evidence':[],'reason':'Claimed support.'},units)
        with self.assertRaises(ValueError):validate_answer({'verdict':'unsupported','evidence':[9],'reason':'Wrong anchor.'},units)
        self.assertEqual(validate_answer({'verdict':'unclear','evidence':[],'reason':'The source is ambiguous.'},units)['verdict'],'unclear')
    def test_unknown_is_not_a_supported_fact(self):
        with self.assertRaises(ValueError):validate_answer({'verdict':'probably','evidence':[0],'reason':'Guess.'},[{'id':0}])

    def test_schema_requires_evidence_for_known_verdict_without_forcing_certainty(self):
        schema=answer_schema([{'id':0},{'id':1}],constrained=True)
        known,unclear=schema['anyOf']
        self.assertEqual(known['properties']['evidence']['minItems'],1)
        self.assertEqual(unclear['properties']['verdict']['const'],'unclear')
        self.assertNotIn('minItems',unclear['properties']['evidence'])
