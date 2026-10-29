#!/usr/bin/env python3
"""Read-only inventory of isolated agent installation assets.

Never reads credential contents, follows symlinks, or changes the installation.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

FILES = (
    "etc/arby-patch-agent/config.json",
    "etc/arby-patch-agent/ca.crt",
    "etc/systemd/system/arby-patch-agent.service",
    "etc/systemd/system/arby-patch-agent.timer",
)
PRIVATE_DIR = "var/lib/arby-patch-agent"


def inspect(root):
    root = Path(root).absolute()
    if root == Path("/"):
        raise ValueError("Live filesystem is forbidden")
    root_info = root.lstat()
    if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.geteuid()
            or root_info.st_mode & 0o022):
        raise ValueError("Unsafe isolated root")
    records = {}
    for relative in FILES:
        path = root
        parts = Path(relative).parts
        missing = False
        for part in parts[:-1]:
            path = path / part
            try:
                info = path.lstat()
            except FileNotFoundError:
                missing = True
                break
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_mode & 0o022):
                raise ValueError(f"Unsafe installation directory: {relative}")
        if missing:
            records[relative] = {"present": False}
            continue
        path = path / parts[-1]
        try:
            info = path.lstat()
        except FileNotFoundError:
            records[relative] = {"present": False}
            continue
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o022 or info.st_nlink != 1
                or info.st_size > 1024 * 1024):
            raise ValueError(f"Unsafe installation asset: {relative}")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError(f"Asset changed during inspection: {relative}")
            with os.fdopen(fd, "rb", closefd=False) as source:
                data = source.read(1024 * 1024 + 1)
        finally:
            os.close(fd)
        if len(data) != info.st_size:
            raise ValueError(f"Asset changed during inspection: {relative}")
        records[relative] = {"present": True, "sha256": hashlib.sha256(data).hexdigest(),
                             "size": len(data), "mode": oct(stat.S_IMODE(info.st_mode))}
    state = root / PRIVATE_DIR
    try:
        info = state.lstat()
    except FileNotFoundError:
        state_status = "absent"
    else:
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise ValueError("Unsafe private state directory")
        state_status = "present-not-inspected"
    return {"product": "Patch Command", "mode": "read-only-isolated-inventory",
            "status": "inspected", "assets": records, "private_state": state_status,
            "credential_contents_read": False, "changes_made": False,
            "production_installed": False, "backup_created": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    try:
        result = inspect(args.root)
    except (OSError, ValueError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
