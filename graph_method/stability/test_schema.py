import unittest
from structured import extraction_schema


class SchemaTests(unittest.TestCase):
    def test_real_ids_and_self_exclusion_are_constrained(self):
        units=[{'id':0,'source':'comment'},{'id':1,'source':'comment'},{'id':2,'source':'title'}]
        schema=extraction_schema(units)
        branches=schema['properties']['arguments']['items']['anyOf']
        self.assertEqual({b['properties']['conclusion']['const'] for b in branches},{0,1})
        for branch in branches:
            cid=branch['properties']['conclusion']['const']
            self.assertNotIn(cid,branch['properties']['premises']['items']['enum'])
            self.assertEqual(set(branch['properties']['premises']['items']['enum']),{0,1,2}-{cid})


if __name__=='__main__':unittest.main()
