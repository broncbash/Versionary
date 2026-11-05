#!/usr/bin/env python3
"""Versionary controlled-beta fresh installation coordinator.

Supports planning and explicitly authorized isolated-root execution.

Real-system installation, upgrades, service activation, and
agent enrollment are deliberately unsupported.
"""

import argparse
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent

AUTHORIZATION = "I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name,
        HERE / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(root, distribution, server, ca_cert):
    planner = load(
        "versionary-agent-beta-fresh-plan.py",
        "versionary_beta76_planner",
    )

    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_beta76_coordinator",
    )

    root = coordinator.validate_root(root)

    payloads = coordinator.prepare(
        distribution,
        server,
        ca_cert,
    )

    plan = planner.inspect_fresh_root(root, payloads)

    return root, payloads, plan


def execute_prepared(root, payloads, authorization):
    """Execute a fresh install only inside an isolated root."""

    if authorization != AUTHORIZATION:
        raise PermissionError(
            "Explicit isolated beta authorization required"
        )

    planner = load(
        "versionary-agent-beta-fresh-plan.py",
        "versionary_beta76_execution_planner",
    )

    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary_beta76_execution_coordinator",
    )

    root = coordinator.validate_root(root)

    # Recheck immediately before invoking the existing writer.
    planner.inspect_fresh_root(root, payloads)

    result = coordinator.install_payloads_isolated(
        root,
        payloads,
    )

    return {
        "status": "isolated_fresh_install_complete",
        "root": str(root),
        "created": result["created"],
        "preserved": result["preserved"],
        "fresh_install_only": True,
        "upgrades_supported": False,
        "real_system_installation_enabled": False,
        "installation_performed": True,
        "services_activated": False,
        "enrollment_performed": False,
    }


def run(
    root,
    distribution,
    server,
    ca_cert,
    execute=False,
    authorization=None,
):
    # Reject invalid execution requests before preparing payloads.
    if execute and authorization != AUTHORIZATION:
        raise PermissionError(
            "Explicit isolated beta authorization required"
        )

    if not execute and authorization is not None:
        raise ValueError(
            "Authorization is only valid with --execute-isolated"
        )

    root, payloads, plan = prepare(
        root,
        distribution,
        server,
        ca_cert,
    )

    if not execute:
        return plan

    return execute_prepared(
        root,
        payloads,
        authorization,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)

    parser.add_argument(
        "--execute-isolated",
        action="store_true",
        help="Execute only into a safe isolated filesystem root",
    )

    parser.add_argument(
        "--authorize-isolated",
        help="Exact isolated-install authorization phrase",
    )

    args = parser.parse_args()

    try:
        result = run(
            root=args.root,
            distribution=args.distribution,
            server=args.server,
            ca_cert=args.ca_cert,
            execute=args.execute_isolated,
            authorization=args.authorize_isolated,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        PermissionError,
    ) as exc:
        parser.exit(1, f"[STOP] {exc}\n")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
