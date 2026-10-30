#!/usr/bin/env python3
"""Explicitly authorized, disposable-only agent installation trial.

Uses the existing onboarding readiness engine and disposable-install-trial.
Does not accept a destination root or perform production installation.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CONFIRMATION = "RUN-DISPOSABLE-TRIAL"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def blocked(reason, readiness=None):
    return {
        "schema_version": 1,
        "product": "Patch Command",
        "workflow": "onboarding-disposable-trial",
        "status": "blocked",
        "reason": reason,
        "readiness": readiness,
        "execution": {
            "performed": False,
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
        },
    }


def execute(*, server, ca_cert, package,
            confirmation=None, os_release="/etc/os-release"):
    if confirmation != CONFIRMATION:
        return blocked("Explicit disposable trial confirmation required")

    if not package:
        return blocked("An explicit agent package is required")

    if not ca_cert:
        return blocked("An existing CA certificate is required")

    onboarding = load("onboard.py", "patch_trial_onboarding")

    preview = onboarding.build_onboarding(
        role="agent",
        server=server,
        ca_cert=ca_cert,
        certificate_mode="existing-ca",
        target="disposable",
        package=package,
        os_release=os_release,
    )

    readiness = preview["readiness"]

    if not readiness["ready_for_isolated_test"]:
        return blocked("Isolated installation preflight failed", readiness)

    # Never allow a production approval flag to become an execution gate.
    # This workflow remains disposable regardless of readiness.
    trial_module = load(
        "disposable-install-trial.py",
        "patch_onboarding_disposable_trial",
    )

    result = trial_module.trial(
        server=server,
        ca_cert=ca_cert,
        package=package,
    )

    if (
        result.get("status") != "passed"
        or result.get("temporary_workspace_cleaned") is not True
        or result.get("production_installed") is not False
        or result.get("systemd_started") is not False
        or result.get("agent_enrolled") is not False
    ):
        raise RuntimeError("Disposable trial returned unsafe or incomplete evidence")

    return {
        "schema_version": 1,
        "product": "Patch Command",
        "workflow": "onboarding-disposable-trial",
        "status": "passed",
        "readiness": readiness,
        "execution": {
            "performed": True,
            "mode": "temporary-workspace-only",
            "staging": result["staging"],
            "temporary_workspace_cleaned": True,
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
            "external_network_requests_made":
                result["external_network_requests_made"],
        },
        "next_action":
            "Review evidence; production deployment remains disabled",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--os-release", default="/etc/os-release")
    parser.add_argument(
        "--confirm",
        help=f"Must equal {CONFIRMATION} to execute a disposable trial",
    )
    args = parser.parse_args(argv)

    try:
        result = execute(
            server=args.server,
            ca_cert=args.ca_cert,
            package=args.package,
            confirmation=args.confirm,
            os_release=args.os_release,
        )
    except (OSError, ValueError, RuntimeError,
            __import__("subprocess").CalledProcessError) as exc:
        result = blocked(f"Disposable trial failed: {exc}")
        result["status"] = "failed"

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
