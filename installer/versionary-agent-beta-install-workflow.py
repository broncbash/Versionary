#!/usr/bin/env python3
"""Controlled Versionary beta installation workflow.

Default: preview only.
Execution: explicitly authorized isolated roots only.
Real-system installation remains disabled.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

AUTHORIZATION = "I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL"


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
        raise ValueError("Absolute root required")

    if root == Path("/") or root.resolve() == Path("/"):
        raise ValueError("Real-system installation disabled")

    if root.is_symlink():
        raise ValueError("Symlinked root forbidden")

    info = root.lstat()

    import stat

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Root must be a directory")

    if info.st_uid != os.geteuid():
        raise ValueError("Root ownership mismatch")

    if info.st_mode & 0o022:
        raise ValueError("Unsafe root permissions")

    return root


def prepare(root, distribution, server, ca_cert):
    root = validate_root(root)

    preflight = load(
        "versionary-agent-system-preflight.py",
        "versionary_beta80_preflight",
    )
    gate = load(
        "versionary-agent-beta-system-fresh-gate.py",
        "versionary_beta80_gate",
    )
    conflicts = load(
        "versionary-agent-system-conflicts.py",
        "versionary_beta80_conflicts",
    )

    preflight.preflight(distribution, server, ca_cert)
    gate.inspect(root)
    conflicts.inspect(root)

    return {
        "root": str(root),
        "status": "ready_for_isolated_beta_install",
        "fresh_install": True,
        "real_system_installation_enabled": False,
        "installation_performed": False,
        "services_activated": False,
        "enrollment_performed": False,
        "production_approved": False,
    }


def execute(root, distribution, server, ca_cert, authorization):
    if authorization != AUTHORIZATION:
        raise PermissionError(
            "Exact isolated beta authorization required"
        )

    plan = prepare(root, distribution, server, ca_cert)

    installer = load(
        "versionary-agent-beta-full-fresh-install.py",
        "versionary_beta80_installer",
    )

    # Reuse the complete isolated installation engine.
    # It independently validates its authorization and root.
    result = installer.run(
        root,
        distribution,
        server,
        ca_cert,
        execute=True,
        authorization=AUTHORIZATION,
    )

    return {
        "plan": plan,
        "installation_result": result,
        "real_system_installation_enabled": False,
        "services_activated": False,
        "enrollment_performed": False,
        "production_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument(
        "--execute-isolated", action="store_true"
    )
    parser.add_argument("--authorize-isolated")
    args = parser.parse_args()

    try:
        if args.execute_isolated:
            result = execute(
                args.root,
                args.distribution,
                args.server,
                args.ca_cert,
                args.authorize_isolated,
            )
        else:
            result = prepare(
                args.root,
                args.distribution,
                args.server,
                args.ca_cert,
            )
    except (OSError, ValueError, RuntimeError, PermissionError) as exc:
        print("[STOP]", exc, file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
