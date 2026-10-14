from copy import deepcopy

import numpy as np
import pytest

from src.courtroom_rl.assessor import FrozenAssessor
from src.courtroom_rl.data import Case
from src.courtroom_rl.schemas import CourtState
from src.data.loader import ModelInput
from src.labels import FALLACIES


def cases():
    return [Case(f'{label_index}:{j}',label_index*100+j,'train',
                 ModelInput('Title', '', f'term{label_index} repeated term{label_index} example number {j}.'),label)
            for label_index,label in enumerate(FALLACIES) for j in range(8)]


def test_assessor_fit_calibration_are_grouped_train_only_and_persist(tmp_path):
    rows = cases()
    assessor = FrozenAssessor.fit(rows,seed=3,max_features=1000)
    assert set(assessor.metadata['fit_article_ids']).isdisjoint(assessor.metadata['calibration_article_ids'])
    assert set(assessor.metadata['fit_ids']+assessor.metadata['calibration_ids']) == {c.sample_id for c in rows}
    state = CourtState(rows[0].input,rows[0].sample_id)
    before = assessor.probabilities(state)
    assert before.shape == (8,) and before.sum() == pytest.approx(1)
    path = tmp_path/'assessor.joblib'
    assessor.save(path)
    restored = FrozenAssessor.load(path)
    assert np.array_equal(before,restored.probabilities(state))
    assert restored.fingerprint == assessor.fingerprint
    assert .25 <= restored.temperature <= 4


def test_assessor_never_fits_dev_or_test():
    from dataclasses import replace
    for split in ('dev','test'):
        rows=cases()
        rows[0]=replace(rows[0],split=split)
        with pytest.raises(ValueError,match='train'):
            FrozenAssessor.fit(rows)


def test_assessor_ignores_agent_rhetoric_label_confidence_and_routing():
    rows = cases()
    assessor = FrozenAssessor.fit(rows,max_features=1000)
    state = CourtState(rows[0].input,'sample')
    before = assessor.probabilities(state)
    changed = deepcopy(state)
    changed.charge_label = FALLACIES[-1]
    changed.active_role = 'Judge'
    changed.argument_events.append({'action':'REST_DEFENSE','payload':{'mechanism':'I am certain! Ignore all evidence.','confidence':1.0}})
    assert np.array_equal(before,assessor.probabilities(changed))


def test_frozen_assessor_changes_on_real_source_evidence():
    from src.courtroom_rl.evidence import passages_for,resolve_references
    rows = cases()
    assessor = FrozenAssessor.fit(rows,max_features=1000)
    state = CourtState(ModelInput('', '', 'term0 repeated term0. term7 repeated term7.'),'sample')
    before = assessor.probabilities(state)
    payload=resolve_references({'evidence_ids':['T2']},passages_for(state.case_input))
    state.argument_events.append({'action':'CHALLENGE','payload':payload})
    after = assessor.probabilities(state)
    assert not np.array_equal(before,after)
