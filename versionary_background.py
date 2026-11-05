"""Versionary development background scan runner. Never installs/starts units.

The runner executes the existing explicit scan in a separate process. It uses
an advisory nonblocking lock to prevent overlapping runs, preserves the agent
identity, and writes no credentials to its operational log.
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import versionary_local_beta as beta


def run_scan(*, execute=subprocess.run, state=None, entry=None, python=None):
    state = Path(state) if state is not None else beta.STATE
    entry = Path(entry) if entry is not None else Path(beta.__file__).resolve()
    python = Path(python) if python is not None else Path(sys.executable)
    if not state.is_dir() or state.is_symlink():
        raise RuntimeError('Private local beta state must already exist')
    if state.stat().st_mode & 0o077:
        raise RuntimeError('State directory is not private (expected mode 0700)')
    if not (state / 'agent.json').is_file() or not (state / 'admin-token').is_file():
        raise RuntimeError('Initialize the local beta before background scanning')
    lock_path = state / 'background-scan.lock'
    if lock_path.is_symlink():
        raise RuntimeError('Refusing symlink lock file')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise RuntimeError('Lock file not owned by current user')
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'already-running', 'scan_started': False}
        started = datetime.now(timezone.utc).isoformat()
        # Never forward scan stdout/stderr into a long-lived log: future errors
        # could accidentally contain credentials or sensitive local paths.
        try:
            completed = execute(
                [str(python), str(entry), 'scan'],
                cwd=str(entry.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=240,
                check=False,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'},
            )
            return {'status': 'success' if completed.returncode == 0 else 'failed',
                    'scan_started': True, 'exit_code': completed.returncode,
                    'started_at': started}
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'scan_started': True, 'started_at': started}
        except OSError:
            return {'status': 'launch-error', 'scan_started': False, 'started_at': started}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description='Versionary local beta background scan test runner')
    parser.add_argument('--dry-run', action='store_true', help='Verify state and show intent without scanning')
    args = parser.parse_args()
    if args.dry_run:
        ready = beta.STATE.is_dir() and beta.AGENT.is_file() and beta.AUTH.is_file()
        print(json.dumps({'mode': 'background-preview', 'ready': ready,
                          'scan_started': False, 'systemd_changed': False}))
        return 0 if ready else 2
    try:
        result = run_scan()
    except RuntimeError as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc), 'scan_started': False}))
        return 2
    print(json.dumps(result))
    return 0 if result['status'] in ('success', 'already-running') else 1


if __name__ == '__main__':
    raise SystemExit(main())
