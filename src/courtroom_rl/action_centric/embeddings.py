"""Frozen, revision-pinned BGE CLS embeddings for public observation relevance."""
from collections import OrderedDict
from functools import lru_cache

import numpy as np
import torch

MODEL = 'BAAI/bge-base-en-v1.5'
REVISION = 'a5beb1e3e68b9ab74eb54cfd186867f64f240e1a'


class FrozenBGE:
    def __init__(self, model=MODEL, revision=REVISION, device='cpu',
                 max_length=512, overlap=64, batch_size=16, cache_size=4096):
        from transformers import AutoModel, AutoTokenizer
        from src.courtroom_rl.data import ROOT
        self.device = torch.device(device)
        if self.device.type == 'cuda' and not torch.cuda.is_available():
            raise ValueError('Embedding CUDA requested but unavailable')
        cache_dir=str(ROOT/'cache/huggingface/hub')
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=revision,
            cache_dir=cache_dir, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(model, revision=revision,
            cache_dir=cache_dir, trust_remote_code=False)
        self.model.to(self.device).eval().requires_grad_(False)
        self.max_length, self.overlap = max_length, overlap
        self.batch_size, self.cache_size = batch_size, cache_size
        content_length = max_length - self.tokenizer.num_special_tokens_to_add(pair=False)
        if not 0 <= overlap < content_length or max_length > self.model.config.max_position_embeddings:
            raise ValueError('Invalid embedding chunk length/overlap')
        if min(batch_size, cache_size) < 1:
            raise ValueError('Embedding batch/cache sizes must be positive')
        self.cache = OrderedDict()

    @torch.inference_mode()
    def encode(self, texts):
        texts = list(texts)
        if not texts:
            return np.empty((0, self.model.config.hidden_size), dtype=np.float32)
        found = {}
        for text in dict.fromkeys(texts):
            if text in self.cache:
                self.cache.move_to_end(text)
                found[text] = self.cache[text]
                continue
            ids = self.tokenizer(text, add_special_tokens=False, truncation=False)['input_ids']
            width = self.max_length - self.tokenizer.num_special_tokens_to_add(pair=False)
            chunks = []
            start = 0
            while True:
                part = ids[start:start + width]
                # The pinned model is BERT: [CLS] text [SEP]. This also works
                # with transformers5, which removed the legacy build helper.
                chunks.append({'input_ids': [self.tokenizer.cls_token_id]+part+[self.tokenizer.sep_token_id]})
                if start + width >= len(ids):
                    break
                start += width - self.overlap
            vectors = []
            for index in range(0, len(chunks), self.batch_size):
                batch = self.tokenizer.pad(chunks[index:index + self.batch_size],
                                           padding=True, return_tensors='pt').to(self.device)
                # BGE's documented pooling: normalized final-layer CLS.
                cls = self.model(**batch).last_hidden_state[:, 0].float()
                vectors.append(torch.nn.functional.normalize(cls, dim=-1))
            # Long text: all overlapping chunks contribute; no silent tail truncation.
            vector = torch.nn.functional.normalize(torch.cat(vectors).mean(0), dim=0)
            value = vector.cpu().numpy().copy()
            if not np.isfinite(value).all():
                raise ValueError('Non-finite embedding')
            found[text] = value
            self.cache[text] = value
            while len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
        return np.stack([found[text] for text in texts])


class FixtureEncoder:
    """Explicit offline fixture only; never selected for real training."""
    def encode(self, texts):
        from src.courtroom_rl.observation import frozen_text
        return np.stack([frozen_text(text) for text in texts])


@lru_cache(maxsize=2)
def _load(options):
    return FrozenBGE(**dict(options))


def encoder_for(config, fixture=False):
    if config.get('observation_mode', 'structural') != 'semantic':
        return None
    if fixture:
        return FixtureEncoder()
    options = config.get('embedding')
    if not options:
        raise ValueError('Semantic observations require explicit embedding config')
    if options.get('model') != MODEL or options.get('revision') != REVISION:
        raise ValueError('Use the pinned BGE model/revision for semantic observations')
    return _load(tuple(sorted(options.items())))
