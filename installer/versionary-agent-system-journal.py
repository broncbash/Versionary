#!/usr/bin/env python3
"""Persistent journal prototype for isolated Versionary installations.

Records installation intent and verifies recovery candidates.
Does not perform installation, deletion, or automatic recovery.
"""

import hashlib
import json
import os
import stat
from pathlib import Path


JOURNAL_NAME = ".versionary-install-journal.json"
JOURNAL_VERSION = 1


class JournalConflict(ValueError):
    pass


def digest(content):
    return hashlib.sha256(content).hexdigest()


def validate_relative(relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("Nonempty relative path required")

    path = Path(relative)

    if (
        path.is_absolute()
        or str(path) != relative
        or any(part in (".", "..") for part in relative.split("/"))
    ):
        raise ValueError(f"Unsafe journal path: {relative}")

    return relative


def make_journal(payloads):
    if not isinstance(payloads, dict) or not payloads:
        raise ValueError("Nonempty payload mapping required")

    files = {}

    for relative, content in payloads.items():
        validate_relative(relative)

        if not isinstance(content, bytes):
            raise TypeError("Journal payloads must be bytes")

        files[relative] = {
            "sha256": digest(content),
            "size": len(content),
            "state": "planned",
        }

    return {
        "version": JOURNAL_VERSION,
        "status": "planned",
        "files": files,
    }


def write_journal(root, journal):
    root = Path(root)

    if not root.is_absolute() or root == Path("/"):
        raise ValueError("Isolated absolute root required")

    info = root.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Unsafe journal root")

    if info.st_mode & 0o022:
        raise ValueError("Writable journal root")

    path = root / JOURNAL_NAME
    data = (
        json.dumps(journal, sort_keys=True, indent=2) + "\n"
    ).encode()

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise

    return path


def read_journal(root):
    root = Path(root)
    path = root / JOURNAL_NAME

    info = path.lstat()

    if not stat.S_ISREG(info.st_mode):
        raise JournalConflict("Unsafe journal file")

    if info.st_nlink != 1 or info.st_mode & 0o077:
        raise JournalConflict("Unsafe journal permissions")

    if info.st_size > 1024 * 1024:
        raise JournalConflict("Journal exceeds size limit")

    data = json.loads(path.read_bytes())

    if (
        data.get("version") != JOURNAL_VERSION
        or data.get("status") != "planned"
        or not isinstance(data.get("files"), dict)
    ):
        raise JournalConflict("Unsupported journal format")

    for relative, entry in data["files"].items():
        validate_relative(relative)

        if (
            not isinstance(entry, dict)
            or entry.get("state") != "planned"
            or not isinstance(entry.get("sha256"), str)
            or len(entry["sha256"]) != 64
            or not isinstance(entry.get("size"), int)
            or entry["size"] < 0
        ):
            raise JournalConflict("Invalid journal entry")

    return data


def inspect_recovery(root, journal):
    """Classify files without modifying the filesystem."""

    root = Path(root)
    results = {}

    for relative, entry in journal["files"].items():
        validate_relative(relative)
        target = root / relative

        try:
            info = target.lstat()
        except FileNotFoundError:
            results[relative] = "absent"
            continue

        if not stat.S_ISREG(info.st_mode):
            raise JournalConflict(
                f"Unsafe recovery target: {relative}"
            )

        if info.st_nlink != 1 or info.st_mode & 0o022:
            raise JournalConflict(
                f"Unsafe recovery target: {relative}"
            )

        if info.st_size != entry["size"]:
            raise JournalConflict(
                f"Recovery target differs: {relative}"
            )

        if digest(target.read_bytes()) != entry["sha256"]:
            raise JournalConflict(
                f"Recovery target differs: {relative}"
            )

        results[relative] = "matches"

    return results
