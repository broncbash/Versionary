"""Validated server settings shared by CLI and admin API.

This is a staging backend: settings do not reconfigure a running TLS proxy.
"""
import ipaddress
import json
import os
import stat
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_PATH = Path('/var/lib/arby-patch-command/settings.json')
DEFAULTS = {'public_url': None, 'enrollment_enabled': False,
            'reporting_enabled': False, 'scan_interval_minutes': 60,
            'appearance': 'cyberpunk', 'tls_mode': 'external'}

class SettingsError(ValueError):
    pass

def validate(values):
    if not isinstance(values, dict) or set(values) != set(DEFAULTS):
        raise SettingsError('Unexpected or missing settings keys')
    data = dict(values)
    url = data['public_url']
    if url is not None:
        if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
            raise SettingsError('public_url must be an HTTPS origin')
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise SettingsError('Invalid public_url') from exc
        if (parsed.scheme != 'https' or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise SettingsError('public_url must be an HTTPS origin')
        if port is not None and not 1 <= port <= 65535:
            raise SettingsError('Invalid public_url port')
        data['public_url'] = url.rstrip('/')
    for key in ('enrollment_enabled', 'reporting_enabled'):
        if type(data[key]) is not bool:
            raise SettingsError(f'{key} must be boolean')
    if type(data['scan_interval_minutes']) is not int or not 5 <= data['scan_interval_minutes'] <= 10080:
        raise SettingsError('scan_interval_minutes must be 5..10080')
    if data['appearance'] not in ('cyberpunk', 'light', 'dark'):
        raise SettingsError('Unsupported appearance')
    if data['tls_mode'] not in ('external', 'local_ca', 'provided'):
        raise SettingsError('Unsupported tls_mode')
    if (data['enrollment_enabled'] or data['reporting_enabled']) and url is None:
        raise SettingsError('public_url required before enabling network features')
    return data

def load(path=DEFAULT_PATH):
    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return dict(DEFAULTS)
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise SettingsError('Settings file must be private and regular')
    try:
        return validate(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError) as exc:
        raise SettingsError('Invalid stored settings') from exc

def save(changes, path=DEFAULT_PATH):
    if not isinstance(changes, dict) or not set(changes).issubset(DEFAULTS):
        raise SettingsError('Unknown settings key')
    path = Path(path)
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise SettingsError('Settings directory must already exist')
    mode = parent.stat().st_mode
    if mode & 0o022:
        raise SettingsError('Settings directory is writable by others')
    current = load(path)
    updated = validate({**current, **changes})
    if path.is_symlink():
        raise SettingsError('Refusing symlink target')
    fd, temp = tempfile.mkstemp(prefix='.arby-settings-', dir=parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(updated, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return updated
