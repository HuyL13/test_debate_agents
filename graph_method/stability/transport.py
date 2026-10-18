"""Shared request pacing and transparent transient-error resumption."""
import os
import time
from pathlib import Path
import msvcrt
from contextlib import contextmanager


@contextmanager
def request_slot(root):
    """Bound concurrent network requests across experiment processes."""
    count=int(os.environ.get('GRAPH_API_CONCURRENCY','2'))
    if not 1<=count<=32:raise ValueError('GRAPH_API_CONCURRENCY must be1..32')
    suffix='_market' if os.environ.get('GRAPH_API_PROVIDER','nvidia').lower()=='market' else ''
    path=Path(root)/('request_slots'+suffix+'.lock')
    with path.open('ab') as init:
        if init.tell()<count:init.write(b'0'*(count-init.tell()))
    with path.open('r+b') as handle:
        chosen=None
        while chosen is None:
            for index in range(count):
                try:
                    handle.seek(index);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);chosen=index;break
                except OSError:pass
            if chosen is None:time.sleep(.2)
        try:yield
        finally:
            handle.seek(chosen);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)


def retryable_cache(record):
    return record.get('status')=='infrastructure_error' and not any(a.get('nonretryable') for a in record.get('attempts',[]))


def pace(root, cooldown=0):
    suffix='_market' if os.environ.get('GRAPH_API_PROVIDER','nvidia').lower()=='market' else ''
    path=Path(root)/('request_pacing'+suffix+'.lock')
    with path.open('ab'):pass
    with path.open('r+b') as handle:
        handle.seek(0,2)
        if handle.tell()==0:handle.write(b'0');handle.flush()
        while True:
            try:
                handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:time.sleep(.2)
        try:
            handle.seek(0);raw=handle.read().decode().strip()
            try:next_at=float(raw)
            except ValueError:next_at=0
            if cooldown:
                next_at=max(next_at,time.time()+cooldown)
            else:
                while next_at>time.time():time.sleep(min(1,next_at-time.time()))
                next_at=time.time()+float(os.environ.get('GRAPH_API_INTERVAL','2.1'))
            handle.seek(0);handle.write(str(next_at).encode());handle.truncate();handle.flush()
        finally:
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
