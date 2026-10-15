"""Bounded episode concurrency; GPU inference is short and serialized."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import threading
import torch

INFERENCE_LOCK=threading.RLock()

def ordered_jobs(function,jobs,workers):
    if type(workers) is not int or workers<1:raise ValueError('workers must be positive')
    jobs=list(jobs)
    if workers==1:return [function(job) for job in jobs]
    with ThreadPoolExecutor(max_workers=min(workers,max(1,len(jobs))),thread_name_prefix='courtroom') as pool:
        return list(pool.map(function,jobs))

def episode_generator(device,seed,phase,index):
    value=int.from_bytes(hashlib.sha256(f'{seed}:{phase}:{index}'.encode()).digest()[:8],'big')%(2**63-1)
    return torch.Generator(device=device).manual_seed(value)

class EpisodeProgress:
    def __init__(self,parent,prefix):self.parent=parent;self.prefix=prefix
    def log(self,stage,message):self.parent.log(stage,f'{self.prefix} {message}')
    def step(self,role,action,target,index):
        if self.parent.verbose_steps:
            self.log('STEP',f'decision={index} {role}.{action}'+(f' target={target}' if target is not None else ''))
    @contextmanager
    def request(self,context,attempt):
        with self.parent.request(f'{self.prefix} {context}',attempt):yield
