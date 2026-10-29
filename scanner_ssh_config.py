"""Optional validated SSH transport configuration for legacy read-only scanners.

If unset, preserve existing deployment defaults. An explicitly configured
invalid path fails closed before any SSH invocation.
"""
import json
import os
import stat
from pathlib import Path

ENV_PATH = "ARBY_SCANNER_SSH_CONFIG_PATH"
DEFAULTS = {
    "identity_file": "/opt/arby-patch-command/keys/scanner_ed25519",
    "known_hosts_file": "/opt/arby-patch-command/keys/known_hosts",
    "username": "arby-scanner",
}


class SSHConfigError(ValueError):
    pass


def _absolute_path(value):
    if (not isinstance(value, str) or not value.startswith("/") or
            len(value) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SSHConfigError("SSH file path must be an absolute safe path")
    path = Path(value)
    if ".." in path.parts or str(path) != value or value.startswith("//"):
        raise SSHConfigError("SSH file path must be normalized")
    return value


def validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULTS):
        raise SSHConfigError("Invalid SSH configuration fields")
    identity = _absolute_path(value["identity_file"])
    known_hosts = _absolute_path(value["known_hosts_file"])
    username = value["username"]
    if (not isinstance(username, str) or not username or len(username) > 32 or
            not username[0].isalpha() or
            any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in username)):
        raise SSHConfigError("Invalid SSH username")
    return {"identity_file": identity, "known_hosts_file": known_hosts,
            "username": username}


def load(path=None):
    selected = path if path is not None else os.environ.get(ENV_PATH)
    if selected is None:
        return dict(DEFAULTS)
    if not isinstance(selected, (str, os.PathLike)) or not str(selected).strip():
        raise SSHConfigError("SSH configuration path is empty")
    config_path = Path(selected)
    try:
        info = config_path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise SSHConfigError("SSH configuration must be private and regular")
        return validate(json.loads(config_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        raise SSHConfigError("Invalid or inaccessible SSH configuration") from exc


def command_options(host):
    """Return SSH arguments; host is validated by scanner_inventory."""
    settings = load()
    return [
        "-T", "-i", settings["identity_file"],
        "-o", "StrictHostKeyChecking=yes",
        "-o", f'UserKnownHostsFile={settings["known_hosts_file"]}',
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-o", "IdentitiesOnly=yes",
        f'{settings["username"]}@{host}',
    ]
