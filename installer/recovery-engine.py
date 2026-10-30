#!/usr/bin/env python3
"""Disposable-only crash recovery engine; never operates on production paths."""
import hashlib
import json
import os
import stat
from pathlib import Path

ASSETS = ('release', 'config', 'ca', 'service', 'timer')

class RecoveryError(RuntimeError):
    pass

class Interrupted(RuntimeError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def safe_read(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RecoveryError('Unsafe asset')
    return path.read_bytes()

def atomic_write(path, data):
    temporary = path.with_name(path.name + '.pending')
    if os.path.lexists(temporary):
        raise RecoveryError('Stale pending file')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)

def validate_root(root):
    root = Path(root).absolute()
    if root == Path('/') or root.is_symlink() or not root.is_dir():
        raise RecoveryError('Disposable test root required')
    info = root.lstat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise RecoveryError('Unsafe disposable root')
    marker = root / '.disposable-recovery-test'
    if not marker.is_file() or marker.is_symlink() or safe_read(marker) != b'v1\n':
        raise RecoveryError('Missing disposable-only marker')
    return root

def initialize(root):
    """Only for newly created, empty private temporary directories."""
    root = Path(root).absolute()
    if root == Path('/') or root.is_symlink() or not root.is_dir() or list(root.iterdir()):
        raise RecoveryError('Fresh empty disposable root required')
    info = root.lstat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise RecoveryError('Private disposable root required')
    (root / 'live').mkdir(mode=0o700)
    (root / 'backup').mkdir(mode=0o700)
    (root / 'candidate').mkdir(mode=0o700)
    atomic_write(root / '.disposable-recovery-test', b'v1\n')
    return root

def prepare(root, previous, candidate):
    root = validate_root(root)
    if set(previous) != set(ASSETS) or set(candidate) != set(ASSETS):
        raise RecoveryError('Incomplete asset set')
    if (root / 'journal.json').exists():
        raise RecoveryError('Transaction already exists')
    if any(any((root / folder).iterdir()) for folder in ('live', 'backup', 'candidate')):
        raise RecoveryError('Test directories must be empty')
    for name in ASSETS:
        if not isinstance(previous[name], bytes) or not isinstance(candidate[name], bytes):
            raise RecoveryError('Asset payload must be bytes')
    for name in ASSETS:
        for folder, value in (('live', previous[name]), ('backup', previous[name]), ('candidate', candidate[name])):
            atomic_write(root / folder / name, value)
    journal = {'version': 1, 'state': 'prepared', 'previous': {n: digest(previous[n]) for n in ASSETS},
               'candidate': {n: digest(candidate[n]) for n in ASSETS}}
    atomic_write(root / 'journal.json', json.dumps(journal, sort_keys=True).encode())
    return journal

def read_journal(root):
    path = root / 'journal.json'
    try:
        journal = json.loads(safe_read(path))
    except (OSError, ValueError, TypeError) as exc:
        raise RecoveryError('Invalid journal') from exc
    if not isinstance(journal, dict) or journal.get('version') != 1 or journal.get('state') not in ('prepared', *ASSETS, 'verified', 'recovered'):
        raise RecoveryError('Invalid journal state')
    if any(set(journal.get(k, {})) != set(ASSETS) for k in ('previous', 'candidate')):
        raise RecoveryError('Invalid journal manifest')
    for key in ('previous', 'candidate'):
        if any(not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v) for v in journal[key].values()):
            raise RecoveryError('Invalid journal digest')
    return journal

def assert_sources(root, journal):
    for name in ASSETS:
        for folder, key in (('backup', 'previous'), ('candidate', 'candidate')):
            if digest(safe_read(root / folder / name)) != journal[key][name]:
                raise RecoveryError('Source integrity mismatch')

def classify_live(root, journal):
    result = {}
    for name in ASSETS:
        value = digest(safe_read(root / 'live' / name))
        if value == journal['previous'][name]:
            result[name] = 'previous'
        elif value == journal['candidate'][name]:
            result[name] = 'candidate'
        else:
            raise RecoveryError('Unknown live asset content')
    return result

def write_state(root, journal, state):
    journal = {**journal, 'state': state}
    atomic_write(root / 'journal.json', json.dumps(journal, sort_keys=True).encode())
    return journal

def apply(root, fail_at=None):
    """Simulate a crash at before:name or after:name; no automatic recovery."""
    root = validate_root(root)
    journal = read_journal(root)
    if journal['state'] != 'prepared':
        raise RecoveryError('Apply requires prepared state')
    assert_sources(root, journal)
    if any(v != 'previous' for v in classify_live(root, journal).values()):
        raise RecoveryError('Unexpected live generation')
    for name in ASSETS:
        if fail_at == 'before:' + name:
            raise Interrupted(fail_at)
        atomic_write(root / 'live' / name, safe_read(root / 'candidate' / name))
        if fail_at == 'after:' + name:
            raise Interrupted(fail_at)
        journal = write_state(root, journal, name)
    if fail_at == 'before:verified':
        raise Interrupted(fail_at)
    journal = write_state(root, journal, 'verified')
    if fail_at == 'after:verified':
        raise Interrupted(fail_at)
    return journal

def recover(root, fail_after=None):
    """Rollback all assets; safe to resume after an interrupted rollback."""
    root = validate_root(root)
    journal = read_journal(root)
    assert_sources(root, journal)
    classify_live(root, journal)  # reject unrelated changes before writing anything
    if journal['state'] == 'recovered':
        if any(v != 'previous' for v in classify_live(root, journal).values()):
            raise RecoveryError('Recovered state changed')
        return journal
    for name in reversed(ASSETS):
        if digest(safe_read(root / 'live' / name)) != journal['previous'][name]:
            atomic_write(root / 'live' / name, safe_read(root / 'backup' / name))
        if fail_after == name:
            raise Interrupted('rollback:' + name)
    return write_state(root, journal, 'recovered')
