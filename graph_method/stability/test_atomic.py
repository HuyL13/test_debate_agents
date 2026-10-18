import unittest
from atomic import validate_splits,apply_splits


class AtomicTests(unittest.TestCase):
    def setUp(self):
        text='If they are passionate the rest of the population must be too.'
        self.units=[{'id':0,'source':'comment','start':0,'end':len(text),'text':text}]
        self.output={'splits':[{'unit_id':0,'parts':['If they are passionate','the rest of the population must be too.']}]}

    def test_exact_partition_and_offsets(self):
        validate_splits(self.output,self.units)
        out=apply_splits(self.output,self.units)
        self.assertEqual(len(out),2)
        for u in out:self.assertEqual(self.units[0]['text'][u['start']:u['end']],u['text'])

    def test_cannot_drop_conditional_or_rewrite_text(self):
        self.output['splits'][0]['parts'][0]='they are passionate'
        with self.assertRaises(ValueError):validate_splits(self.output,self.units)
        self.output['splits'][0]['parts'][0]='If they are very passionate'
        with self.assertRaises(ValueError):validate_splits(self.output,self.units)

    def test_no_split_is_lossless(self):
        self.assertEqual(apply_splits({'splits':[]},self.units),self.units)

    def test_token_cuts_preserve_source_without_copying_quotes(self):
        from atomic_tokens import apply_cuts,validate_cuts
        cut={'cuts':[{'unit_id':0,'before':[4]}]}
        validate_cuts(cut,self.units)
        out=apply_cuts(cut,self.units)
        self.assertEqual(out[0]['text'],'If they are passionate')
        self.assertEqual(out[1]['text'],'the rest of the population must be too.')

    def test_out_of_range_token_cut_is_rejected(self):
        from atomic_tokens import validate_cuts
        with self.assertRaises(ValueError):validate_cuts({'cuts':[{'unit_id':0,'before':[999]}]},self.units)


if __name__=='__main__':unittest.main()
