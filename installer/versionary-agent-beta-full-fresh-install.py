#!/usr/bin/env python3
"""Fresh-only complete Versionary agent installation in isolated roots.

Uses the existing verified offline installer. Does not install into /,
enroll agents, activate services, or perform upgrades.

The underlying multi-stage installer is not globally atomic.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
AUTHORIZATION = "I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL"

BLOCKED = (
    "opt/versionary-agent/agent",
    "opt/versionary-agent/releases",
    "opt/versionary-agent/.install.lock",
    "var/lib/versionary-agent/identity.json",
    "var/lib/versionary-agent/credential.json",
    "var/lib/versionary-agent/enrollment.json",
)

JOURNALS = (
    ".versionary-install-journal.json",
    ".versionary-upgrade-transaction",
)


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(root):
    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_full77_coordinator",
    )
    root = coordinator.validate_root(root)

    for relative in JOURNALS:
        target = root / relative
        if target.exists() or target.is_symlink():
            raise RuntimeError(
                f"Pending recovery state requires review: {relative}"
            )

    for relative in BLOCKED:
        target = root / relative
        if target.exists() or target.is_symlink():
            raise RuntimeError(
                f"Existing agent installation requires review: {relative}"
            )

    # Detect unknown existing application/state entries rather than
    # silently treating an incomplete installation as fresh.
    for relative in (
        "opt/versionary-agent",
        "var/lib/versionary-agent",
    ):
        target = root / relative
        if target.is_symlink():
            raise RuntimeError(
                f"Symlinked installation directory: {relative}"
            )
        if target.exists():
            info = target.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError(
                    f"Unsafe installation directory: {relative}"
                )
            if any(target.iterdir()):
                raise RuntimeError(
                    f"Nonempty installation directory: {relative}"
                )

    # The five-file planner additionally checks the expected CLI,
    # config, CA, service and timer destinations when given payloads.
    return {
        "status": "ready_for_isolated_full_fresh_install",
        "root": str(root),
        "fresh_install_only": True,
        "module_count": 13,
        "real_system_installation_enabled": False,
        "installation_performed": False,
        "services_activated": False,
        "enrollment_performed": False,
    }


def prepare(root, distribution, server, ca_cert):
    planner = load(
        "versionary-agent-beta-fresh-plan.py",
        "versionary_full77_planner",
    )
    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_full77_prepare",
    )

    root = coordinator.validate_root(root)
    payloads = coordinator.prepare(
        distribution, server, ca_cert
    )

    planner.inspect_fresh_root(root, payloads)
    result = inspect(root)

    return root, payloads, result


def run(
    root,
    distribution,
    server,
    ca_cert,
    *,
    execute=False,
    authorization=None,
):
    if execute and authorization != AUTHORIZATION:
        raise PermissionError(
            "Explicit isolated-install authorization required"
        )

    if not execute and authorization is not None:
        raise ValueError(
            "Authorization requires --execute-isolated"
        )

    root, payloads, result = prepare(
        root, distribution, server, ca_cert
    )

    if not execute:
        return result

    # Repeat checks immediately before invoking the writer.
    planner = load(
        "versionary-agent-beta-fresh-plan.py",
        "versionary_full77_recheck",
    )
    planner.inspect_fresh_root(root, payloads)
    inspect(root)

    offline = load(
        "install-agent-offline.py",
        "versionary_full77_offline",
    )

    # This existing installer verifies the distribution, installs
    # all 13 agent modules, the CLI, CA, config and unit files.
    # It performs multiple stages; failures can leave partial state.
    offline.install(root, distribution, server, ca_cert)

    agent = root / "opt/versionary-agent/agent"
    if not agent.is_symlink():
        raise RuntimeError(
            "Complete agent installation missing active release"
        )

    return {
        "status": "isolated_full_fresh_install_complete",
        "root": str(root),
        "module_count": 13,
        "fresh_install_only": True,
        "installation_performed": True,
        "real_system_installation_enabled": False,
        "services_activated": False,
        "enrollment_performed": False,
        "upgrades_supported": False,
        "globally_atomic": False,
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
        result = run(
            args.root,
            args.distribution,
            args.server,
            args.ca_cert,
            execute=args.execute_isolated,
            authorization=args.authorize_isolated,
        )
    except Exception as exc:
        parser.exit(1, f"[STOP] {exc}\n")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
