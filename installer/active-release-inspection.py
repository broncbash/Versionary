#!/usr/bin/env python3
"""Read-only active release inspection for isolated Versionary installations.

Does not verify release contents, change files, or authorize rollback.
"""

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path


def safe_directory(path):
    info = path.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o022
    ):
        raise ValueError(f"Unsafe installation directory: {path}")


def absent():
    return {
        "product": "Versionary",
        "mode": "isolated-active-release-inspection",
        "status": "inspected",
        "active_release": None,
        "active_present": False,
        "changes_made": False,
        "production_approved": False,
    }


def inspect(root):
    root = Path(root).absolute()

    if root == Path("/"):
        raise ValueError("Live root forbidden")

    safe_directory(root)

    app = root

    # A partial installation may contain configuration and systemd assets
    # without having installed the agent code yet.
    for part in ("opt", "versionary-agent"):
        app = app / part

        try:
            safe_directory(app)
        except FileNotFoundError:
            return absent()

    active = app / "agent"

    try:
        info = active.lstat()
    except FileNotFoundError:
        # The app directory exists, but no release is active.
        # Still reject an unsafe releases directory if one exists.
        releases = app / "releases"
        try:
            safe_directory(releases)
        except FileNotFoundError:
            pass
        return absent()

    if not stat.S_ISLNK(info.st_mode):
        raise ValueError("Active release pointer is not a symlink")

    target = os.readlink(active)
    match = re.fullmatch(r"releases/([0-9a-f]{64})/agent", target)

    if not match:
        raise ValueError("Unsafe active release target")

    identifier = match.group(1)

    releases = app / "releases"
    safe_directory(releases)
    safe_directory(releases / identifier)
    safe_directory(releases / identifier / "agent")

    return {
        "product": "Versionary",
        "mode": "isolated-active-release-inspection",
        "status": "inspected",
        "active_release": identifier,
        "active_present": True,
        "changes_made": False,
        "production_approved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)

    try:
        result = inspect(args.root)
    except (OSError, ValueError) as exc:
        print(f"Active release inspection refused: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
