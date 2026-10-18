import unittest
from patterns import mine_patterns,retrieve,bootstrap_recovery


class PatternTests(unittest.TestCase):
    def records(self):
        rows=[]
        for label,op in [('L1','consensus'),('L2','testimony')]:
            for i in range(8):
                rows.append({'sample_id':label+str(i),'article_id':label+str(i),'gold':label,'status':'accepted','extraction':{'arguments':[{'premises':[0],'conclusion':1,'operator':op,'stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[]}]}})
        return rows

    def test_article_support_not_number_of_edges_or_duplicates(self):
        rows=self.records()
        patterns=mine_patterns(rows,min_articles=5)
        self.assertEqual(set(p['label'] for p in patterns),{'L1','L2'})
        for p in patterns:self.assertEqual(p['positive_articles'],8)
        duplicates=[dict(rows[0],sample_id=str(i)) for i in range(20)]
        self.assertEqual(mine_patterns(duplicates,min_articles=5),[])

    def test_generic_argument_shape_never_learned_as_class_core(self):
        for p in mine_patterns(self.records()):self.assertIn('operator',p['constraints'])

    def test_retrieval_maps_existing_graph_argument_and_source_nodes(self):
        patterns=mine_patterns(self.records())
        out=retrieve(patterns,self.records()[0])
        self.assertEqual(out[0]['label'],'L1')
        self.assertEqual(out[0]['mapping'],{'premise':'u0','inference':'a0','conclusion':'u1'})

    def test_bootstrap_is_reproducible(self):
        rows=self.records();patterns=mine_patterns(rows)
        self.assertEqual(bootstrap_recovery(patterns,rows,rounds=10),bootstrap_recovery(patterns,rows,rounds=10))


if __name__=='__main__':unittest.main()
