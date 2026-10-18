import time
import unittest
import io
import json
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch
from core import batch

class BulkFailureGuardTests(unittest.TestCase):
    def test_guarded_cli_does_not_exit_as_success(self):
        import pipeline_v2
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'manifest.json').write_text(json.dumps({'samples':[{'sample_id':'x'}]}),encoding='utf-8')
            with patch.object(pipeline_v2,'ROOT',Path(tmp)),patch.object(pipeline_v2,'run_source',return_value=([],{'stopped_early':True,'complete':False})),patch('sys.argv',['pipeline_v2.py','--manifest','manifest.json']),redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as context:pipeline_v2.main()
            self.assertEqual(context.exception.code,2)
    def test_small_pilot_is_not_rejected_before_window(self):
        from pipeline_v2 import source_failure_guard
        self.assertIsNone(source_failure_guard([{'status':'proposal_failed'}]*24))
    def test_bad_bulk_is_stopped_after_enough_completed_samples(self):
        from pipeline_v2 import source_failure_guard
        self.assertTrue(source_failure_guard([{'status':'proposal_failed'}]*32))
        self.assertIsNone(source_failure_guard([{'status':'accepted'}]*32))
    def test_failure_guard_cancels_queued_work_and_keeps_finished_results(self):
        started=[]
        def work(i):
            started.append(i);time.sleep(.005);return i
        rows=batch(list(range(200)),work,'guard-test',workers=2,stop_when=lambda rows:'stop test' if len(rows)>=2 else None)
        self.assertLess(len(started),200)
        self.assertEqual(set(rows),set(started))
