"""Run-local request and usage logs; contexts do not leak across sessions."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from .ai_role_transport import append_json, now

current_run = ContextVar('psiarena_run', default=None)

@dataclass
class RunLog:
    directory: Path
    call_count: int = 0

    def next_call(self, role):
        self.call_count += 1
        return self.directory / 'requests' / f'{self.call_count:05d}_{role}'

    def record_usage(self, role, usage):
        append_json(self.directory / 'usage.jsonl', {'at': now(), 'role': role, 'usage': usage})

@contextmanager
def run_log(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    token = current_run.set(RunLog(directory))
    try:
        yield
    finally:
        current_run.reset(token)
