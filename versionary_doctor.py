#!/usr/bin/env python3
"""Versionary local beta read-only readiness doctor. No state mutation."""
import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.versionary-local-beta'
PREVIEWS = [ROOT / '.versionary-timer-integration-preview', ROOT / '.versionary-timer-preview']

def check(name, ok, detail, severity='error'):
    return {'name': name, 'status': 'pass' if ok else ('warn' if severity == 'warning' else 'fail'), 'detail': detail}

def inspect(root=ROOT):
    root = Path(root)
    results = []
    py = root / '.venv/bin/python'
    results.append(check('python_venv', py.is_file() and os.access(py, os.X_OK), 'Virtualenv Python executable'))
    for name in ('versionary_local_beta.py', 'versionary_background.py', 'versionary_timer_integration.py'):
        results.append(check('source_' + name, (root / name).is_file(), 'Required local beta source: ' + name))
    state = root / '.versionary-local-beta'
    state_ok = state.is_dir() and not state.is_symlink()
    results.append(check('state_directory', state_ok, 'Local beta state exists and is not a symlink'))
    if state_ok:
        s = state.stat()
        results.append(check('state_permissions', s.st_uid == os.getuid() and not (stat.S_IMODE(s.st_mode) & 0o077), 'State owned by current user, no group/other access'))
        for name in ('agent.json', 'admin-token'):
            p = state / name
            present = p.is_file() and not p.is_symlink()
            results.append(check('identity_' + name, present, 'Private identity file exists: ' + name))
            if present:
                s = p.stat()
                results.append(check('permissions_' + name, s.st_uid == os.getuid() and not (stat.S_IMODE(s.st_mode) & 0o077), 'Identity file owner and access mode'))
        lock = state / 'background-scan.lock'
        results.append(check('lock_symlink', not lock.is_symlink(), 'Lock path must not be a symlink'))
    previews = [root / '.versionary-timer-integration-preview', root / '.versionary-timer-preview']
    for preview in previews:
        results.append(check('preview_' + preview.name, not preview.is_symlink(), 'Preview path must not be a symlink'))
        if preview.is_dir() and not preview.is_symlink():
            for name in ('versionary-beta-scan.service', 'versionary-beta-scan.timer'):
                p = preview / name
                if p.exists():
                    results.append(check('preview_file_' + preview.name + '_' + name, p.is_file() and not p.is_symlink(), 'Preview unit must be regular file'))
    return results

def main():
    parser = argparse.ArgumentParser(description='Read-only Versionary beta readiness diagnostics')
    parser.add_argument('--json', action='store_true', help='Output machine-readable JSON only')
    parser.add_argument('--root', type=Path, default=ROOT, help='Repository root (for offline tests)')
    args = parser.parse_args()
    checks = inspect(args.root)
    failures = sum(c['status'] == 'fail' for c in checks)
    report = {'product': 'Versionary', 'mode': 'read-only-offline-doctor', 'checks': checks,
              'passed': sum(c['status'] == 'pass' for c in checks), 'failed': failures,
              'production_approved': False, 'timer_activated_by_doctor': False,
              'real_scans': 0, 'secrets_in_report': False}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in checks:
            print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
        print(f"Summary: {report['passed']} passed, {failures} failed. No changes made.")
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
