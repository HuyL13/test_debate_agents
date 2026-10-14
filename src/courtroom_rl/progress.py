"""Small console-only training progress; no prompts, credentials or new logs."""
from contextlib import contextmanager
import threading
import time


class ConsoleProgress:
    def __init__(self, verbose_steps=False, emit=None, heartbeat_seconds=30):
        self.verbose_steps = verbose_steps
        self.emit = emit or (lambda text:print(text,flush=True))
        self.started = time.monotonic()
        self.heartbeat_seconds = heartbeat_seconds
        self.lock = threading.Lock()

    def log(self,stage,message):
        elapsed = int(time.monotonic()-self.started)
        hours, remainder = divmod(elapsed,3600)
        minutes, seconds = divmod(remainder,60)
        with self.lock:
            self.emit(f'[{hours:02d}:{minutes:02d}:{seconds:02d}] [{stage}] {message}')

    def step(self,role,action,target,index):
        if self.verbose_steps:
            self.log('STEP',f'decision={index} {role}.{action}'+(f' target={target}' if target is not None else ''))

    @contextmanager
    def request(self,context,attempt):
        started = time.monotonic()
        stop = threading.Event()
        self.log('API',f'{context} attempt={attempt}{" (retry)" if attempt > 1 else ""}: waiting for response')
        def heartbeat():
            while not stop.wait(self.heartbeat_seconds):
                self.log('API',f'{context} attempt={attempt}: still waiting ({time.monotonic()-started:.0f}s)')
        thread = threading.Thread(target=heartbeat,name='courtroom-api-heartbeat',daemon=True)
        thread.start()
        try:
            yield
        except Exception as exc:
            self.log('API',f'{context} attempt={attempt}: {type(exc).__name__} after {time.monotonic()-started:.1f}s')
            raise
        else:
            self.log('API',f'{context} attempt={attempt}: response received in {time.monotonic()-started:.1f}s (validation follows)')
        finally:
            stop.set()
            thread.join()
