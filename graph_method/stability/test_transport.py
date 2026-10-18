import unittest
import tempfile
from pathlib import Path
from transport import retryable_cache,pace,request_slot

class TransportTests(unittest.TestCase):
    def test_only_transient_infrastructure_is_resumed(self):
        self.assertTrue(retryable_cache({'status':'infrastructure_error','attempts':[{'rejection_reasons':['HTTP Error 429: Too Many Requests']}]}))
        self.assertFalse(retryable_cache({'status':'accepted'}))
        self.assertFalse(retryable_cache({'status':'quality_rejected'}))
        self.assertFalse(retryable_cache({'status':'infrastructure_error','attempts':[{'nonretryable':True}]}))

    def test_cooldown_file_remains_one_timestamp(self):
        with tempfile.TemporaryDirectory() as root:
            pace(root,cooldown=1);pace(root,cooldown=2)
            self.assertGreater(float((Path(root)/'request_pacing.lock').read_text()),0)

    def test_request_slot_releases_on_error(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                with request_slot(root):raise ValueError('simulated request failure')
            with request_slot(root):
                with request_slot(root):pass
