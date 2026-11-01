"""Snapshots preserve the original single-call control during cleanup."""
import hashlib
import pytest
from src.baseline.single import system_prompt


@pytest.mark.parametrize('task,patterns,expected',[
    ('detection',False,'2fd7cddd85ed2fa9354e6d998a19aabc6f6aedd2a83b2b86311b407a64d4fa8c'),
    ('detection',True,'1aa171b28443847804e3aa500c9cc4f1c9499920882bc97525bb8fa3aa2b3148'),
    ('classification',False,'d60e32ae27bbd5aea005e2d3617c9465c3f26dc380e2a205678072911d60befc'),
    ('classification',True,'7e44ab5648e7dcf3ab9133abbd7f3f20ca3b38cfc9c43a8379abc422efe2ffd0'),
])
def test_single_prompt_snapshot(task,patterns,expected):
    assert hashlib.sha256(system_prompt(task,patterns).encode()).hexdigest()==expected
