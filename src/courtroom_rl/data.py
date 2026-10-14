"""Verified, user-approved flat classification data; no parallel preprocessing."""
from dataclasses import dataclass
import json
from pathlib import Path

from src.data.loader import ModelInput
from src.labels import FALLACIES
from src.io_utils import file_hash
from src.courtroom_rl.vendor.baseline.loader import load_split, select_task


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Case:
    sample_id: str
    article_id: int
    split: str
    input: ModelInput
    gold: str


def load_cases(split, data_dir=None):
    if split not in ('train', 'dev', 'test'):
        raise ValueError('Use an official train/dev/test split')
    directory = Path(data_dir) if data_dir else ROOT/'data/cocolofa/classification'
    provenance = json.loads((directory/'provenance.json').read_text(encoding='utf-8-sig'))
    path = directory/f'{split}.json'
    if file_hash(path) != provenance['splits'][split]['sha256']:
        raise ValueError(f'{split} classification checksum differs from pinned provenance')
    records = select_task(load_split(path),'classification')
    cases, seen = [], set()
    for sample in records:
        if sample.gold('classification') not in FALLACIES or sample.sample_id in seen:
            raise ValueError('Invalid classification label or duplicate sample ID')
        seen.add(sample.sample_id)
        cases.append(Case(sample.sample_id, sample.article_id, split,
                          sample.model_input(context='paper'), sample.gold('classification')))
    if len(cases) != provenance['splits'][split]['count']:
        raise ValueError('Classification count differs from provenance')
    return cases
