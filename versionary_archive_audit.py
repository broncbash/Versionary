#!/usr/bin/env python3
"""Offline, read-only source archive safety and portability audit."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile
import zipfile

PRIVATE_PARTS = {'.git', '.venv', '__pycache__', '.versionary-local-beta', '.versionary-timer-preview', '.versionary-timer-integration-preview', '.env', 'node_modules'}
PRIVATE_NAMES = {'admin-token', 'agent.json', 'agents.db', 'id_rsa', 'id_ed25519'}
PRIVATE_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db')


def check_name(raw):
    if not raw or '\\' in raw or '\x00' in raw:
        return 'invalid filename'
    p = PurePosixPath(raw)
    if p.is_absolute() or any(x in ('..', '') for x in raw.split('/')):
        return 'unsafe archive path'
    parts = [x for x in p.parts if x != '.']
    if not parts:
        return 'empty path'
    if any(x in PRIVATE_PARTS for x in parts) or any(x in PRIVATE_NAMES for x in parts):
        return 'private runtime or credential path'
    if parts[-1].lower().endswith(PRIVATE_SUFFIXES):
        return 'potential secret or database file'
    return None


def audit(path):
    issues = []
    names = set()
    files = 0
    bytes_total = 0
    def entry(name, kind, size):
        nonlocal files, bytes_total
        issue = check_name(name)
        if issue:
            issues.append({'path': name, 'issue': issue})
        norm = str(PurePosixPath(name))
        if norm in names:
            issues.append({'path': name, 'issue': 'duplicate entry'})
        names.add(norm)
        if kind not in ('file', 'dir'):
            issues.append({'path': name, 'issue': f'unsupported entry type: {kind}'})
        if kind == 'file':
            files += 1
            bytes_total += size
        if size > 100 * 1024 * 1024:
            issues.append({'path': name, 'issue': 'individual file exceeds 100 MiB'})
    if tarfile.is_tarfile(path):
        with tarfile.open(path, 'r:*') as archive:
            for m in archive:
                kind = 'file' if m.isfile() else 'dir' if m.isdir() else 'link' if m.issym() or m.islnk() else 'special'
                entry(m.name, kind, m.size)
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for m in archive.infolist():
                mode = m.external_attr >> 16
                kind = 'link' if stat.S_ISLNK(mode) else 'dir' if m.is_dir() else 'file'
                entry(m.filename, kind, m.file_size)
    else:
        raise ValueError('unsupported archive (expected tar or zip)')
    if not files:
        issues.append({'path': '', 'issue': 'archive contains no regular files'})
    if bytes_total > 1024 * 1024 * 1024:
        issues.append({'path': '', 'issue': 'unpacked file content exceeds 1 GiB'})
    return {'status': 'passed' if not issues else 'failed', 'archive': str(path), 'regular_files': files, 'unpacked_bytes': bytes_total, 'issues': issues, 'extracted': False, 'installed': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if not args.archive.is_file() or args.archive.is_symlink():
            raise ValueError('archive must be a regular non-symlink file')
        result = audit(args.archive)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as e:
        result = {'status': 'failed', 'issues': [{'path': '', 'issue': str(e)}], 'extracted': False, 'installed': False}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Archive audit: {result['status'].upper()}")
        print(f"Files: {result.get('regular_files', 0)}")
        for issue in result['issues']:
            print(f"[FAIL] {issue['path']}: {issue['issue']}")
        print('Read-only: no extraction or installation performed.')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
