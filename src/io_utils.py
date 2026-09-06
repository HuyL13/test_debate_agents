import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     suffix='.tmp', delete=False) as stream:
        name = stream.name
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    os.replace(name, path)


def append_jsonl(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def recover_audit_tail(path):
    """Quarantine only a torn final write, preserving bytes for investigation."""
    path = Path(path)
    if not path.exists():
        return
    lines = path.read_bytes().splitlines(keepends=True)
    for index, line in enumerate(lines):
        try:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError('Expected audit object')
        except (ValueError, UnicodeDecodeError) as exc:
            if index != len(lines) - 1 or line.endswith(b'\n'):
                raise ValueError(f'Corrupt interior audit record {index + 1}') from exc
            quarantine = path.with_name(f'{path.stem}.interrupted.{uuid.uuid4().hex}.bin')
            quarantine.write_bytes(line)
            temporary = path.with_suffix('.recovery.tmp')
            temporary.write_bytes(b''.join(lines[:index]))
            temporary.replace(path)
            return
    if lines and not lines[-1].endswith(b'\n'):
        with path.open('ab') as stream:
            stream.write(b'\n')
