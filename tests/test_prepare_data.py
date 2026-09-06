import subprocess
import sys
from pathlib import Path

import pytest


def test_prepare_exports_exact_git_blobs_despite_windows_checkout(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / 'upstream' / 'cocolofa'
    if not source.exists():
        pytest.skip('Optional real upstream clone integration')
    result = subprocess.run([sys.executable, str(root / 'scripts/prepare_data.py'),
                             '--source', str(source), '--dest', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    expected = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:test.json'])
    assert (tmp_path / 'test.json').read_bytes() == expected
