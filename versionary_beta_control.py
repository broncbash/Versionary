"""Versionary Beta 0.2: explicit local observer CLI and inert timer preview.

No unit installation, activation, network discovery or package upgrades.
"""
import argparse
import json
import os
import shlex
import stat
import sys
from pathlib import Path

import versionary_local_beta as beta

INTERVAL = '6h'


def identity():
    if not beta.AGENT.is_file():
        return None
    data = json.loads(beta.AGENT.read_text())
    return {'id': data['id'], 'distro': data.get('distro', 'linux')}


def status():
    record = identity()
    result = {
        'mode': 'local-development-observer',
        'state': str(beta.STATE),
        'initialized': beta.AUTH.is_file() and beta.DB.is_file(),
        'agent': record,
        'scheduler': 'not-managed-by-this-tool',
        'updates_installed': False,
    }
    if beta.DB.is_file() and record:
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(f'file:{beta.DB}?mode=ro', uri=True)) as conn:
            row = conn.execute(
                '''SELECT a.hostname, a.last_seen, r.timestamp, r.status, r.count
                   FROM agents a LEFT JOIN scan_reports r ON r.id = (
                     SELECT id FROM scan_reports WHERE agent_id=a.id
                     ORDER BY id DESC LIMIT 1)
                   WHERE a.id=?''', (record['id'],)
            ).fetchone()
        if row:
            result['hostname'], result['last_seen'], result['last_scan'], result['scan_status'], result['updates'] = row
    print(json.dumps(result, indent=2))


def plan():
    root = Path(__file__).resolve().parent
    python = root / '.venv/bin/python'
    entry = root / 'versionary_local_beta.py'
    for path in (root, python, entry):
        if '\n' in str(path) or '\r' in str(path):
            raise SystemExit('Unsupported newline in path')
    # These are *preview files* inside the repository, not user systemd units.
    out = root / '.versionary-timer-preview'
    out.mkdir(mode=0o700, exist_ok=True)
    os.chmod(out, 0o700)
    service = ('[Unit]\nDescription=Versionary local beta read-only package scan\n'
               '[Service]\nType=oneshot\n'
               f'WorkingDirectory={root}\n'
               f'ExecStart={python} {entry} scan\n'
               'NoNewPrivileges=yes\nPrivateTmp=yes\n')
    timer = ('[Unit]\nDescription=Versionary local beta scan schedule (inactive preview)\n'
             '[Timer]\nOnBootSec=10min\nOnUnitActiveSec=6h\nPersistent=false\n'
             'Unit=versionary-beta-scan.service\n'
             '[Install]\nWantedBy=timers.target\n')
    for name, content in (('versionary-beta-scan.service', service), ('versionary-beta-scan.timer', timer)):
        p = out / name
        if p.is_symlink():
            raise SystemExit('Refusing symlink timer preview')
        fd = os.open(p, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.chmod(p, 0o600)
    print('INACTIVE timer preview created:', out)
    print('Cadence: every 6 hours after an initial 10-minute delay.')
    print('No systemd units installed, enabled, or started.')
    print('Review these files before approving activation.')


def main():
    parser = argparse.ArgumentParser(description='Versionary Beta 0.2 observer controls')
    parser.add_argument('command', choices=['status', 'scan', 'timer-preview'])
    args = parser.parse_args()
    if args.command == 'status':
        status()
    elif args.command == 'scan':
        if not beta.AGENT.exists():
            raise SystemExit('Initialize first: ./.venv/bin/python versionary_local_beta.py init')
        beta.scan()
    else:
        plan()


if __name__ == '__main__':
    main()
