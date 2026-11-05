#!/usr/bin/env python3
"""Versionary beta release preflight and source-package builder (no deployment)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

REQUIRED = ('versionary_local_beta.py', 'versionary_background.py', 'versionary_timer_integration.py', 'versionary_doctor.py')
DENY_DIRS = {'.git', '.venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.versionary-local-beta', '.versionary-timer-preview', '.versionary-timer-integration-preview', 'node_modules', 'dist', 'build'}
DENY_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db', '.pyc', '.log', '.tar', '.gz', '.zip'}
DENY_NAMES = {'admin-token', 'agent.json', '.env', '.env.local', 'id_rsa', 'id_ed25519', 'credentials.json', 'secrets.json'}
ALLOW_SUFFIXES = {'.py', '.md', '.toml', '.txt', '.yaml', '.yml', '.json', '.css', '.js', '.html', '.svg', '.sh', '.service', '.timer'}
MAX_FILE = 2 * 1024 * 1024

def is_safe_file(root, path):
    rel = path.relative_to(root)
    if any(part in DENY_DIRS or part.startswith('.versionary-') for part in rel.parts[:-1]):
        return False
    if path.name in DENY_NAMES or path.suffix.lower() in DENY_SUFFIXES:
        return False
    if path.suffix.lower() not in ALLOW_SUFFIXES:
        return False
    if path.is_symlink() or not path.is_file():
        return False
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_size > MAX_FILE:
        return False
    if any(part.startswith('.') for part in rel.parts):
        return False
    return True

def collect(root):
    files = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in DENY_DIRS and not d.startswith('.') and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            p = Path(base) / name
            if is_safe_file(root, p):
                files.append(p)
    return files

def preflight(root):
    checks = []
    for name in REQUIRED:
        p = root / name
        checks.append({'check': name, 'ok': p.is_file() and not p.is_symlink()})
    for name in ('.versionary-local-beta', '.versionary-timer-preview'):
        p = root / name
        checks.append({'check': f'{name}:not_symlink', 'ok': not p.is_symlink()})
    return checks

def manifest(root, files):
    return {'product': 'Versionary', 'artifact': 'beta-source-preview', 'production_approved': False,
            'deployable': False, 'files': [{'path': p.relative_to(root).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in files]}

def main(argv=None):
    parser = argparse.ArgumentParser(description='Versionary offline source-release preview (never deploys)')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, help='Write a preview source archive here (outside the repository)')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error('root is not a directory')
    checks = preflight(root)
    files = collect(root)
    data = manifest(root, files)
    data['checks'] = checks
    data['passed'] = all(c['ok'] for c in checks)
    data['file_count'] = len(files)
    data['archive_written'] = False
    if args.output:
        out = args.output.expanduser().absolute()
        if out.exists() or out.is_symlink():
            parser.error('output already exists; refusing overwrite')
        if out == root or root in out.parents:
            parser.error('output must be outside repository')
        if not data['passed']:
            parser.error('preflight failed; refusing archive')
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(out, 'x:gz') as tar:
                for p in files:
                    # Recheck against symlink swaps before adding.
                    if not is_safe_file(root, p):
                        raise RuntimeError('file changed during packaging')
                    tar.add(p, arcname='versionary/' + p.relative_to(root).as_posix(), recursive=False)
            data['archive_written'] = True
            data['archive_path'] = str(out)
        except BaseException:
            out.unlink(missing_ok=True)
            raise
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Versionary source preview: {len(files)} allowlisted files, {sum(c['ok'] for c in checks)}/{len(checks)} preflight checks")
        print('PRODUCTION APPROVED: NO | DEPLOYABLE: NO')
        if args.output:
            print('Archive:', data.get('archive_path', 'not created'))
        for c in checks:
            if not c['ok']:
                print('FAIL:', c['check'])
    return 0 if data['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())
