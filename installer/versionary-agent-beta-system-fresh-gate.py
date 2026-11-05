#!/usr/bin/env python3
"""Read-only fresh-install gate for controlled Versionary beta.

No installation, service activation, enrollment or cleanup.
An empty, explicitly selected installation target is required.
"""

import argparse
import json
import os
import stat
from pathlib import Path

APPLICATION = "opt/versionary-agent"
STATE = "var/lib/versionary-agent"

DESTINATIONS = (
    "etc/versionary-agent",
    "etc/systemd/system/versionary-agent.service",
    "etc/systemd/system/versionary-agent.timer",
)

JOURNALS = (
    ".versionary-install-journal.json",
    ".versionary-upgrade-transaction",
)

def check_directory(path, label):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "absent"

    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"Unsafe {label}: {path}")

    if info.st_mode & 0o022:
        raise RuntimeError(f"Writable {label}: {path}")

    if info.st_uid != os.geteuid():
        raise RuntimeError(f"Unexpected owner: {path}")

    return "existing"

def check_absent(path, label):
    try:
        path.lstat()
    except FileNotFoundError:
        return

    raise RuntimeError(f"Existing {label} requires review: {path}")

def check_empty(path, label):
    state = check_directory(path, label)
    if state == "existing" and any(path.iterdir()):
        raise RuntimeError(f"Nonempty {label}: {path}")
    return state

def inspect(root):
    root = Path(root)

    if not root.is_absolute():
        raise ValueError("Absolute installation root required")

    if ".." in root.parts:
        raise ValueError("Parent traversal forbidden")

    # This is a read-only gate, including when root is '/'.
    # It never authorizes writing to the selected root.
    if check_directory(root, "installation root") == "absent":
        raise FileNotFoundError(
            f"Installation root does not exist: {root}"
        )

    for relative in JOURNALS:
        check_absent(root / relative, "recovery journal")

    # Existing application and private state must never be
    # silently interpreted as a fresh installation.
    application = check_empty(
        root / APPLICATION, "application directory"
    )
    state = check_empty(
        root / STATE, "private state directory"
    )

    for relative in DESTINATIONS:
        check_absent(root / relative, "installation destination")

    return {
        "status": "fresh_install_destinations_clear",
        "root": str(root),
        "application_directory": application,
        "state_directory": state,
        "installation_performed": False,
        "real_system_installation_enabled": False,
        "services_activated": False,
        "enrollment_performed": False,
        "production_approved": False,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    try:
        result = inspect(args.root)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"[STOP] {exc}\n")

    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
