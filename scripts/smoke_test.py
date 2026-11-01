"""Offline end-to-end dialectical plumbing; no real model or dataset required."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.loader import ModelInput
from src.engine import Engine
from src.llm.client import Client,ModelConfig


def main():
    rows=[]
    with TemporaryDirectory() as tmp:
        for task in ['classification','detection']:
            settings=[('single','adversarial'),('adaptive','adversarial')]
            for mode,policy in settings:
                folder=Path(tmp)/f'{task}-{mode}-{policy}'
                client=Client(ModelConfig(name='offline-fixture',provider='mock'),folder/'cache.sqlite3',folder/'calls.jsonl')
                result=Engine(client,task=task,mode=mode,adaptive_policy=policy).run(
                    ModelInput('Synthetic news','','We have always done this, so we should continue.'),{})
                rows.append(dict(task=task,mode=mode,policy=policy,prediction=result['prediction'],synthetic=True))
    print(json.dumps(dict(status='complete',synthetic=True,runs=rows),indent=2))


if __name__=='__main__':main()
