import unittest
from copy import deepcopy
from test_patterns_v2 import fixture
from direct_graph_retrieval import GraphIndex

class DirectGraphTests(unittest.TestCase):
    def test_gold_of_query_does_not_change_ranking(self):
        index=GraphIndex([fixture(i) for i in range(8)])
        query=fixture(99);first=index.search(query)
        query['gold']='OTHER'
        self.assertEqual(first,index.search(query))
    def test_retrieves_without_five_article_threshold(self):
        index=GraphIndex([fixture(1)])
        self.assertEqual(index.search(fixture(99))[0]['sample_id'],'1')
    def test_source_article_and_id_excluded(self):
        index=GraphIndex([fixture(1),fixture(2)])
        self.assertEqual([x['sample_id'] for x in index.search(fixture(1))],['2'])
    def test_direction_and_scheme_change_reduce_similarity(self):
        same=fixture(1);different=fixture(2)
        different['annotation']['applications'][0].update(scheme='consensus',roles=[])
        different['annotation']['applications'][0].update(premises=[2,1],target=0)
        index=GraphIndex([different,same])
        ranked=index.search(fixture(99))
        self.assertEqual(ranked[0]['sample_id'],'1')
        self.assertGreater(ranked[0]['score'],ranked[1]['score'] if len(ranked)>1 else 0)

if __name__=='__main__':unittest.main()
