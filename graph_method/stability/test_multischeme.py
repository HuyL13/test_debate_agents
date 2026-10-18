import unittest
from multischeme import expand,validate_multi,compile_multi


class MultiTests(unittest.TestCase):
    def setUp(self):
        self.units=[{'id':i,'source':'comment','text':str(i),'start':i,'end':i+1} for i in range(3)]
        self.output={'arguments':[{'conclusion':2,'warrants':[{'kind':'testimony','premises':[0]},{'kind':'consensus','premises':[1]}],'stance':'uses','commitment':'certain','scope_change':'na','alternatives':'na','chain':[],'escalation':'na'}]}

    def test_separate_warrants_keep_their_own_premise_bindings(self):
        validate_multi(self.output,self.units)
        expanded,joint=expand(self.output)
        self.assertEqual(expanded['arguments'][0]['premises'],[0])
        self.assertEqual(expanded['arguments'][1]['premises'],[1])
        self.assertEqual(joint,[0,0])

    def test_group_node_preserves_joint_move(self):
        graph=compile_multi(self.output,self.units)
        self.assertTrue(any(n['kind']=='reasoning_move' for n in graph['nodes']))
        self.assertEqual(sum(e['rel']=='IMPLEMENTS_MOVE' for e in graph['edges']),2)

    def test_each_warrant_still_rejects_self_premise(self):
        self.output['arguments'][0]['warrants'][0]['premises']=[2]
        with self.assertRaises(ValueError):validate_multi(self.output,self.units)


if __name__=='__main__':unittest.main()
