#!/usr/bin/env python3
"""Integrated Versionary agent installation for isolated roots only.

This module deliberately cannot install into /.
It does not start services, enroll agents, or modify packages.
Recovery is conservative: unresolved journals require review.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent

MODES = {
    "opt/versionary-agent/versionary_agent_cli.py": 0o644,
    "etc/versionary-agent/config.json": 0o600,
    "etc/versionary-agent/ca.crt": 0o644,
    "etc/systemd/system/versionary-agent.service": 0o644,
    "etc/systemd/system/versionary-agent.timer": 0o644,
}


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_root(root):
    root = Path(root)

    if not root.is_absolute():
        raise ValueError("Absolute isolated root required")

    if root == Path("/"):
        raise ValueError("Real-system installation forbidden")

    if root.is_symlink():
        raise ValueError("Symlinked installation root forbidden")

    info = root.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Installation root must be a directory")

    if info.st_mode & 0o022:
        raise ValueError("Writable installation root forbidden")

    if info.st_uid != os.geteuid():
        raise ValueError("Installation root ownership mismatch")

    return root


def prepare(distribution, server, ca_cert):
    preflight = load(
        "versionary-agent-system-preflight.py",
        "versionary_isolated_preflight",
    )
    content = load(
        "versionary-agent-system-content.py",
        "versionary_isolated_content",
    )

    preflight.preflight(distribution, server, ca_cert)

    payloads = content.expected_payloads(
        distribution, server, ca_cert
    )

    if set(payloads) != set(MODES):
        raise ValueError("Unexpected installation payload inventory")

    return payloads


def install_payloads_isolated(root, payloads, fail_after=None):
    root = validate_root(root)

    if not isinstance(payloads, dict) or set(payloads) != set(MODES):
        raise ValueError("Unexpected installation payload inventory")

    for name, content in payloads.items():
        if not isinstance(content, bytes) or not content:
            raise ValueError(f"Invalid installation payload: {name}")

    conflicts = load(
        "versionary-agent-system-conflicts.py",
        "versionary_isolated_conflicts",
    )
    content_module = load(
        "versionary-agent-system-content.py",
        "versionary_isolated_existing_content",
    )
    recovery = load(
        "versionary-agent-system-recovery.py",
        "versionary_isolated_recovery",
    )

    pending = recovery.inspect_pending(root)

    if pending["status"] != "clear":
        raise RuntimeError(
            "Pending installation journal requires review"
        )

    conflicts.inspect(root)
    content_module.inspect_existing(
        root, payloads, expected_uid=os.geteuid()
    )

    return recovery.install_isolated(
        root, payloads, modes=MODES, fail_after=fail_after
    )


def install(root, distribution, server, ca_cert):
    root = validate_root(root)
    payloads = prepare(distribution, server, ca_cert)
    return install_payloads_isolated(root, payloads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument(
        "--execute-isolated",
        action="store_true",
        help="Explicitly authorize isolated-root installation",
    )
    args = parser.parse_args()

    try:
        root = validate_root(args.root)
        payloads = prepare(
            args.distribution, args.server, args.ca_cert
        )

        if not args.execute_isolated:
            print("[OK] Preflight passed")
            print("[OK] Isolated root:", root)
            print("[OK] Payloads:", len(payloads))
            print("[OK] No installation performed")
            return 0

        result = install_payloads_isolated(root, payloads)

        print("[OK] Isolated installation complete")
        print("[OK] Created:", result["created"])
        print("[OK] Preserved:", result["preserved"])
        print("[OK] No services activated")
        print("[OK] No enrollment performed")
        return 0

    except (OSError, ValueError, RuntimeError) as exc:
        print("[STOP]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
