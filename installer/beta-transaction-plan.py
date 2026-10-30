"""Read-only beta transaction intent. Not a transaction executor or rollback.

The manifest describes requested assets before mutation. It intentionally does
not imply that an existing installation is safe to replace or recover.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = (
    ('release', 'opt/arby-patch-agent/agent', 'symlink'),
    ('config', 'etc/arby-patch-agent/config.json', 'file'),
    ('ca', 'etc/arby-patch-agent/ca.crt', 'file'),
    ('service', 'etc/systemd/system/arby-patch-agent.service', 'file'),
    ('timer', 'etc/systemd/system/arby-patch-agent.timer', 'file'),
)


def _load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def build(root, server, ca_data, package):
    """Validate destinations and return deterministic, non-secret intent metadata."""
    root = Path(root).absolute()
    if root == Path('/') or root.is_symlink() or not root.is_dir():
        raise ValueError('An existing non-root beta directory is required')
    if not isinstance(ca_data, bytes):
        raise ValueError('CA content must be bytes')
    _load('beta-preflight.py', 'beta_plan_preflight').inspect(root, server, ca_data, package)
    modules = _load('validate-package.py', 'beta_plan_package').load_modules(package)
    identifier = _load('atomic-release.py', 'beta_plan_release').release_id(modules)
    expected = {
        'release': f'releases/{identifier}/agent'.encode(),
        'config': json.dumps({'server': server, 'ca_cert': '/etc/arby-patch-agent/ca.crt'},
                             sort_keys=True, separators=(',', ':')).encode(),
        'ca': ca_data,
        'service': (HERE / 'systemd/arby-patch-agent.service').read_bytes(),
        'timer': (HERE / 'systemd/arby-patch-agent.timer').read_bytes(),
    }
    return {
        'schema': 1,
        'mode': 'isolated-beta-read-only-plan',
        'root': str(root),
        'release_id': identifier,
        'assets': [
            {'name': name, 'path': path, 'kind': kind,
             'sha256': hashlib.sha256(expected[name]).hexdigest()}
            for name, path, kind in ASSETS
        ],
        'changes_made': False,
        'recovery_available': False,
        'production_approved': False,
    }
