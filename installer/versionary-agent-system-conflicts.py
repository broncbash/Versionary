#!/usr/bin/env python3
"""Read-only destination checks for Versionary system beta installation."""

import os
import stat
from pathlib import Path


DIRECTORIES = (
    ("opt", 0o755),
    ("opt/versionary-agent", 0o755),
    ("etc", 0o755),
    ("etc/versionary-agent", 0o755),
    ("etc/systemd", 0o755),
    ("etc/systemd/system", 0o755),
    ("var", 0o755),
    ("var/lib", 0o755),
    ("var/lib/versionary-agent", 0o700),
)

FILES = (
    "opt/versionary-agent/versionary_agent_cli.py",
    "etc/versionary-agent/config.json",
    "etc/versionary-agent/ca.crt",
    "etc/systemd/system/versionary-agent.service",
    "etc/systemd/system/versionary-agent.timer",
)


def inspect_directory(path, expected_mode, expected_uid):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "absent"

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"Unsafe directory destination: {path}")

    if info.st_uid != expected_uid:
        raise ValueError(f"Unexpected directory owner: {path}")

    mode = stat.S_IMODE(info.st_mode)

    if mode & 0o022:
        raise ValueError(f"Writable directory destination: {path}")

    if expected_mode == 0o700 and mode != 0o700:
        raise ValueError(f"Private state mode mismatch: {path}")

    return "existing"


def inspect_file(path, expected_uid):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "absent"

    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Unsafe file destination: {path}")

    if info.st_uid != expected_uid:
        raise ValueError(f"Unexpected file owner: {path}")

    if info.st_nlink != 1:
        raise ValueError(f"Hardlinked file destination: {path}")

    if info.st_mode & 0o022:
        raise ValueError(f"Writable file destination: {path}")

    return "existing"


def inspect(root, expected_uid=None):
    root = Path(root)

    if not root.is_absolute():
        raise ValueError("Absolute installation root required")

    if expected_uid is None:
        expected_uid = os.geteuid()

    root_info = root.lstat()

    if not stat.S_ISDIR(root_info.st_mode):
        raise ValueError("Unsafe installation root")

    if root_info.st_uid != expected_uid:
        raise ValueError("Unexpected installation root owner")

    if root_info.st_mode & 0o022:
        raise ValueError("Writable installation root")

    result = {"directories": {}, "files": {}}

    for relative, mode in DIRECTORIES:
        result["directories"][relative] = inspect_directory(
            root / relative,
            mode,
            expected_uid,
        )

    for relative in FILES:
        result["files"][relative] = inspect_file(
            root / relative,
            expected_uid,
        )

    return result
