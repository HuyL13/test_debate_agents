"""Convenience entrypoint; all implementation lives in courtroom_rl.runner."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.courtroom_rl.runner import main


if __name__ == '__main__':
    result = main(['smoke', *sys.argv[1:]])
    if result and result.get('failed', 0):
        raise SystemExit(1)
