import unittest
from unittest.mock import patch
from paper_trials import process

class SourceCheckTests(unittest.TestCase):
    def test_factored_answers_do_not_see_draft_or_each_other(self):
        units=[{'id':0,'source':'comment','text':'Most believe it.','start':0,'end':16},{'id':1,'source':'comment','text':'It is true.','start':17,'end':28}]
        sample={'sample_id':'fixture','gold':'unused','comment':'Most believe it. It is true.'}
        baseline={'units':units,'source_call_id':'baseline','extraction':{'arguments':[]}}
        captured=[]
        def fake(model,stage,sid,system,user,validator,version,*args,**kwargs):
            captured.append((version,user))
            output='PRIVATE_DRAFT_MARKER' if version=='v14-free-draft' else 'ANSWER_'+version if version.startswith('v16-source-') else {'arguments':[]}
            return {'status':'accepted','call_id':version,'output':output}
        with patch('paper_trials.invoke',side_effect=fake):process((sample,baseline),'verified_draft')
        questions=[user for version,user in captured if version.startswith('v16-source-')]
        self.assertEqual(len(questions),2)
        for user in questions:
            self.assertEqual(set(user),{'source','units'})
            self.assertNotIn('PRIVATE_DRAFT_MARKER',str(user))
            self.assertNotIn('ANSWER_',str(user))
