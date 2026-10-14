"""Frozen train-only source classifier; no generated arguments or gold in input."""
from pathlib import Path
import os
import joblib
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from src.labels import FALLACIES
from src.io_utils import digest, file_hash
from src.courtroom_rl.reward import source_evidence_view
from src.courtroom_rl.schemas import CourtState


def text_view(state):
    view = source_evidence_view(state)
    return '\n'.join(str(v) for v in view['input'].values()) + '\n' + '\n'.join(s[3] for s in view['source_evidence'])


class UniformAssessor:
    fingerprint = 'fixture-uniform-v1'
    def probabilities(self, state):
        return np.full(len(FALLACIES), 1 / len(FALLACIES))


class FrozenAssessor:
    @classmethod
    def fit(cls, cases, seed=0, max_features=20000):
        if not cases or any(c.split != 'train' for c in cases):
            raise ValueError('Assessor fitting accepts train only')
        fit, calibration = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(cases, groups=[c.article_id for c in cases]))
        if {cases[i].gold for i in fit} != set(FALLACIES):
            raise ValueError('Train fitting partition must contain all classes')
        obj = cls()
        obj.vectorizer = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True, max_features=max_features)
        obj.model = LogisticRegression(C=2, class_weight='balanced', max_iter=400, random_state=seed)
        texts = [text_view(CourtState(c.input,c.sample_id)) for c in cases]
        # Fit original and source-excerpt emphasis views, with identical labels.
        from src.courtroom_rl.evidence import passages_for
        augmented, labels = [], []
        for i in fit:
            excerpts = list(passages_for(cases[i].input))
            augmented.append(texts[i]); labels.append(cases[i].gold)
            if excerpts:
                # Passage records are source-grounded; no agent text is included.
                for p in (excerpts[0], excerpts[-1]):
                    quote = p['text']
                    augmented.append(texts[i]+'\n'+quote); labels.append(cases[i].gold)
        obj.model.fit(obj.vectorizer.fit_transform(augmented), labels)
        logits = obj.model.decision_function(obj.vectorizer.transform([texts[i] for i in calibration]))
        targets = np.array([list(obj.model.classes_).index(cases[i].gold) for i in calibration])
        loss = lambda temperature: float(-np.log(np.maximum(softmax(logits/temperature,axis=1)[np.arange(len(targets)),targets],1e-12)).mean())
        obj.temperature = float(minimize_scalar(loss,bounds=(.25,4),method='bounded').x)
        obj.metadata = {'version':1,'seed':seed,'max_features':max_features,
            'data_hash':digest([(c.sample_id,c.article_id,c.input.as_dict(),c.gold) for c in cases]),
            'fit_ids':[cases[i].sample_id for i in fit], 'calibration_ids':[cases[i].sample_id for i in calibration],
            'fit_article_ids':sorted({cases[i].article_id for i in fit}),
            'calibration_article_ids':sorted({cases[i].article_id for i in calibration}),
            'calibration_nll':loss(obj.temperature)}
        obj.fingerprint = digest(obj.metadata)
        return obj

    def probabilities(self,state):
        logits = self.model.decision_function(self.vectorizer.transform([text_view(state)]))[0]
        probs = softmax(logits/self.temperature)
        return np.array([probs[list(self.model.classes_).index(label)] for label in FALLACIES])

    def save(self,path):
        path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        temporary = path.with_suffix('.tmp')
        joblib.dump(self,temporary)
        os.replace(temporary,path)
        self.fingerprint = file_hash(path)

    @classmethod
    def load(cls,path):
        obj = joblib.load(path)
        if not isinstance(obj,cls) or obj.metadata['version'] != 1:
            raise ValueError('Unsupported assessor artifact')
        obj.fingerprint = file_hash(path)
        return obj
