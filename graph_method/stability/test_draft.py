import unittest
from core import parse_output

class DraftTests(unittest.TestCase):
    def test_plain_annotation_is_preserved(self):
        annotation='Unit0 is a proposed reason; unit1 rejects its sufficiency.\n'
        self.assertEqual(parse_output(annotation,'text'),annotation)
    def test_json_contract_is_not_weakened(self):
        with self.assertRaises(ValueError):parse_output('unstructured annotation','json')
        self.assertEqual(parse_output('```json\n{"arguments":[]}\n```','json'),{'arguments':[]})
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):parse_output('{}','unknown')
