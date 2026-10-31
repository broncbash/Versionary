"""Read-only, fail-closed destination preflight for isolated beta staging.

This is NOT a transactional rollback engine. No production paths permitted.
"""
import importlib.util
import json
import os
import stat
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def safe_directory(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError(f'Unsafe beta directory: {path}')
    return True

def safe_file(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError(f'Unsafe beta destination: {path}')
    return path.read_bytes()

def inspect(root, server, ca_data, package):
    root = Path(root).absolute()
    if root == Path('/') or not safe_directory(root):
        raise ValueError('Preflight requires an existing isolated beta root')
    # Validate every existing ancestor; do not follow symlinks into host paths.
    for relative in ('opt', 'opt/versionary-agent', 'opt/versionary-agent/releases',
                     'var', 'var/lib', 'var/lib/versionary-agent',
                     'etc', 'etc/versionary-agent', 'etc/systemd', 'etc/systemd/system'):
        safe_directory(root / relative)
    app = root / 'opt/versionary-agent'
    active = app / 'agent'
    release = load('atomic-release.py', 'beta_preflight_release')
    validator = load('validate-package.py', 'beta_preflight_validator')
    modules = validator.load_modules(package)
    identifier = release.release_id(modules)
    expected_link = f'releases/{identifier}/agent'
    try:
        info = active.lstat()
    except FileNotFoundError:
        info = None
    if info is not None:
        if not stat.S_ISLNK(info.st_mode) or os.readlink(active) != expected_link:
            raise ValueError('Existing beta release differs; explicit migration required')
        target = app / expected_link
        if not safe_directory(target):
            raise ValueError('Missing active beta release')
        found = {}
        for item in target.iterdir():
            if item.name == '__pycache__':
                release.require_safe_bytecode_cache(item)
                continue
            if item.name not in modules:
                raise ValueError('Unexpected beta release module')
            found[item.name] = safe_file(item)
        if found != modules:
            raise ValueError('Existing beta release content differs')
    elif (app / 'releases' / identifier).exists():
        # A partial release may be present from an interrupted installation.
        # Do not attempt to interpret it as safe to overwrite.
        raise ValueError('Unactivated beta release exists; manual inspection required')
    config = root / 'etc/versionary-agent/config.json'
    data = safe_file(config)
    if data is not None:
        expected = {'server': server, 'ca_cert': '/etc/versionary-agent/ca.crt'}
        try:
            actual = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError('Invalid existing beta configuration') from exc
        if actual != expected:
            raise ValueError('Existing beta configuration differs')
    existing_ca = safe_file(root / 'etc/versionary-agent/ca.crt')
    if existing_ca is not None and existing_ca != ca_data:
        raise ValueError('Existing beta CA differs')
    for name in ('versionary-agent.service', 'versionary-agent.timer'):
        existing = safe_file(root / 'etc/systemd/system' / name)
        if existing is not None and existing != (HERE / 'systemd' / name).read_bytes():
            raise ValueError(f'Existing beta systemd unit differs: {name}')
    return {'status': 'preflight-passed', 'changes_made': False}
