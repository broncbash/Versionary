#!/usr/bin/env python3
"""Read-only fresh-install planning for Versionary controlled beta.

This module never installs files, activates services, enrolls
agents, or authorizes installation into the live system root.

In-place upgrades are outside the initial beta scope.
"""

import argparse
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_fresh_root(root, payloads):
    """Evaluate a fresh isolated installation without modifying it."""

    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_beta_fresh_coordinator",
    )

    conflicts = load(
        "versionary-agent-system-conflicts.py",
        "versionary_beta_fresh_conflicts",
    )

    content = load(
        "versionary-agent-system-content.py",
        "versionary_beta_fresh_content",
    )

    recovery = load(
        "versionary-agent-system-recovery.py",
        "versionary_beta_fresh_recovery",
    )

    root = coordinator.validate_root(root)

    if not isinstance(payloads, dict):
        raise ValueError("Payload mapping required")

    if set(payloads) != set(coordinator.MODES):
        raise ValueError("Unexpected installation payload inventory")

    if any(
        not isinstance(value, bytes) or not value
        for value in payloads.values()
    ):
        raise ValueError("Invalid installation payload")

    upgrade_journal = root / ".versionary-upgrade-transaction"

    if upgrade_journal.exists() or upgrade_journal.is_symlink():
        raise RuntimeError(
            "Pending upgrade transaction blocks fresh installation"
        )

    pending = recovery.inspect_pending(root)

    if pending["status"] != "clear":
        raise RuntimeError(
            "Pending installation recovery blocks fresh installation"
        )

    inventory = conflicts.inspect(root)

    existing = content.inspect_existing(
        root,
        payloads,
        expected_uid=None,
    )

    occupied = [
        name
        for name, status in existing.items()
        if status != "absent"
    ]

    if occupied:
        raise RuntimeError(
            "Fresh installation requires absent payload destinations: "
            + ", ".join(sorted(occupied))
        )

    return {
        "status": "ready_for_isolated_fresh_install",
        "root": str(root),
        "payload_count": len(payloads),
        "payloads": sorted(payloads),
        "existing_directories": sorted(
            name
            for name, status in inventory["directories"].items()
            if status == "existing"
        ),
        "fresh_install_only": True,
        "upgrades_supported": False,
        "real_system_installation_enabled": False,
        "installation_performed": False,
        "services_activated": False,
        "enrollment_performed": False,
    }


def plan(root, distribution, server, ca_cert):
    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_beta_fresh_prepare",
    )

    root = coordinator.validate_root(root)

    payloads = coordinator.prepare(
        distribution,
        server,
        ca_cert,
    )

    return inspect_fresh_root(root, payloads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)

    args = parser.parse_args()

    try:
        result = plan(
            args.root,
            args.distribution,
            args.server,
            args.ca_cert,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"[STOP] {exc}\n")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
