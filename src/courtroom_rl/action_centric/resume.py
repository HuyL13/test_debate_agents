"""Explicit source-pair compatibility; never globally disable source checks."""
import json
from pathlib import Path
from src.courtroom_rl.data import ROOT

REGISTRY=ROOT/'docs/diagnostics/resume-source-migrations.json'


def source_migration(previous,current,registry=None):
    path=Path(registry) if registry is not None else REGISTRY
    if not path.exists():return None
    for entry in json.loads(path.read_text(encoding='utf-8')):
        if entry.get('from_source')==previous and entry.get('to_source')==current and entry.get('reason'):
            return dict(entry)
    return None
