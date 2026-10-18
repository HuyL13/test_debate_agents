import unittest
from schema_ablation import simple_schema

class AblationTests(unittest.TestCase):
    def test_simple_schema_leaves_cross_field_checks_to_validator(self):
        schema=simple_schema([{'id':0,'source':'comment'},{'id':1,'source':'comment'},{'id':2,'source':'title'}])
        item=schema['properties']['arguments']['items']
        self.assertNotIn('anyOf',item)
        self.assertEqual(item['properties']['conclusion']['enum'],[0,1])
        self.assertEqual(item['properties']['premises']['items']['enum'],[0,1,2])
