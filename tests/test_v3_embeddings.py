import numpy as np
import pytest
import torch

from src.courtroom_rl.action_centric.embeddings import FrozenBGE
from src.courtroom_rl.action_centric.env import CourtroomEnv
from src.courtroom_rl.action_centric.executor import FixtureExecutor
from src.courtroom_rl.action_centric.observation import encode
from src.data.loader import ModelInput
from src.courtroom_rl.action_centric.state import ROLE_ACTIONS


@pytest.fixture
def encoder(tmp_path):
    from transformers import BertConfig, BertModel, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models, pre_tokenizers, processors
    vocab = ['[PAD]', '[UNK]', '[CLS]', '[SEP]', '[MASK]', 'old', 'practice',
             'best', 'competing', 'reason', 'nature', '.', 'title', 'parent']
    backend = Tokenizer(models.WordPiece(dict(zip(vocab, range(len(vocab)))), unk_token='[UNK]'))
    backend.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    backend.post_processor = processors.TemplateProcessing(single='[CLS] $A [SEP]',
        special_tokens=[('[CLS]', 2), ('[SEP]', 3)])
    tokenizer = PreTrainedTokenizerFast(tokenizer_object=backend, unk_token='[UNK]',
        pad_token='[PAD]', cls_token='[CLS]', sep_token='[SEP]', mask_token='[MASK]')
    tokenizer.save_pretrained(tmp_path)
    torch.manual_seed(17)
    model = BertModel(BertConfig(vocab_size=len(vocab), hidden_size=16,
        num_hidden_layers=1, num_attention_heads=2, intermediate_size=24,
        max_position_embeddings=32))
    model.save_pretrained(tmp_path)
    return FrozenBGE(str(tmp_path), revision='local-test', device='cpu',
                     max_length=16, overlap=2, batch_size=2)


def test_real_transformer_frozen_normalized_cached_and_long_text(encoder):
    assert not encoder.model.training
    assert all(not p.requires_grad for p in encoder.model.parameters())
    text = 'old practice ' * 24 + 'nature'
    vectors = encoder.encode([text, 'competing reason', text])
    assert vectors.shape == (3, 16)
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
    np.testing.assert_array_equal(vectors[0], vectors[2])
    calls = []
    hook = encoder.model.register_forward_hook(lambda *args: calls.append(1))
    np.testing.assert_array_equal(encoder.encode([text])[0], vectors[0])
    assert not calls
    hook.remove()
    # Text beyond the first chunk must contribute instead of being truncated.
    assert not np.allclose(vectors[0], encoder.encode(['old practice ' * 7])[0], atol=1e-7)


def test_neural_relevance_reaches_actor_observation_without_gold(encoder):
    env = CourtroomEnv(FixtureExecutor(), semantic_observation=True, text_encoder=encoder)
    env.reset(ModelInput('title', 'parent', 'old practice. best competing reason.'))
    semantic = encode(env)
    env.semantic_observation = False
    structural = encode(env)
    assert semantic.shape == structural.shape
    assert np.isfinite(semantic).all()
    assert not np.array_equal(semantic, structural)
    assert all('gold' not in text for text in encoder.cache)
    env.state.active_role = 'Judge'
    structural = encode(env)
    env.semantic_observation = True
    semantic = encode(env)
    index = ROLE_ACTIONS['Judge'].index('REQUEST_REBUTTAL') * 7
    assert semantic[index] != structural[index]
