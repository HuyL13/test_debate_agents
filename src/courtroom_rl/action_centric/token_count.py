"""Pinned Llama3-compatible BPE admission estimate, not byte-as-token counting."""
import math
import json
from pathlib import Path
from src.io_utils import file_hash
from src.courtroom_rl.data import ROOT


class Llama3TokenCounter:
    name='llama3-bpe-framing-margin-v1'

    def __init__(self,path,sha256):
        self.path=Path(path)
        if not self.path.is_file():
            raise ValueError(f'Missing pinned tokenizer: {path}; restore tokenizer artifact before a live run')
        self.fingerprint=file_hash(self.path)
        if self.fingerprint!=sha256:raise ValueError('Tokenizer checksum differs from pinned configuration')
        from tokenizers import Tokenizer
        self.tokenizer=Tokenizer.from_file(str(self.path))

    def __call__(self,payload):
        count=8
        for message in payload['messages']:
            content=message.get('content','')
            if not isinstance(content,str):raise ValueError('Text-only token counter cannot estimate image messages')
            count+=12+len(self.tokenizer.encode(content,add_special_tokens=False).ids)
        if payload.get('response_format',{}).get('type')=='json_schema':
            count+=len(self.tokenizer.encode(json.dumps(payload['response_format'],ensure_ascii=False),add_special_tokens=False).ids)
        # Shared Llama3 vocabulary; provider chat framing can differ, so add
        # both fixed and proportional margin. Actual usage is always authoritative.
        return math.ceil(count*1.05)+256


def load_counter(config,model_name):
    options=config.get('tokenizer')
    if not options:return None
    if not model_name.startswith(options['model_prefix']):
        raise ValueError('Configured tokenizer does not match selected model family')
    return Llama3TokenCounter(ROOT/options['path'],options['sha256'])
