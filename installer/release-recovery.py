"""Durable recovery marker for isolated agent code-release trials.

Not a production transaction manager. Only accepts a pre-existing safe test root.
"""
import json
import os
import re
import stat
import tempfile
from pathlib import Path

IDENTIFIER = re.compile(r"[0-9a-f]{64}\Z")
MARKER = ".release-recovery.json"


def safe_app(root):
    root = Path(root).absolute()
    if root == Path("/"):
        raise ValueError("Production root is forbidden")
    for path in (root, root / "opt", root / "opt/arby-patch-agent"):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError("Unsafe isolated directory")
    return root / "opt/arby-patch-agent"


def _identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid release identifier")
    return value


def _sync(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _marker(app):
    return app / MARKER


def write(root, *, previous, candidate):
    app = safe_app(root)
    previous, candidate = _identifier(previous), _identifier(candidate)
    marker = _marker(app)
    if marker.is_symlink() or marker.exists():
        raise RuntimeError("Unresolved recovery marker already exists")
    data = json.dumps({"version": 1, "previous": previous, "candidate": candidate},
                      sort_keys=True).encode("utf-8")
    fd, name = tempfile.mkstemp(prefix=".recovery-pending-", dir=app)
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        # Refuse overwriting an existing marker even if another caller races us.
        os.link(name, marker, follow_symlinks=False)
        _sync(app)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read(root):
    app = safe_app(root)
    marker = _marker(app)
    fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or info.st_size > 4096):
            raise ValueError("Unsafe recovery marker")
        with os.fdopen(fd, "rb", closefd=False) as source:
            record = json.loads(source.read())
    finally:
        os.close(fd)
    if (not isinstance(record, dict) or set(record) != {"version", "previous", "candidate"}
            or record["version"] != 1):
        raise ValueError("Invalid recovery marker schema")
    _identifier(record["previous"])
    _identifier(record["candidate"])
    return record


def clear(root):
    app = safe_app(root)
    read(root)
    _marker(app).unlink()
    _sync(app)


def recover(root, atomic):
    """Restore validated prior code release. Caller must hold installer lock."""
    app = safe_app(root)
    record = read(root)
    # activate_release validates prior release contents before changing the link.
    atomic.activate_release(app, record["previous"])
    clear(root)
    return record["previous"]
