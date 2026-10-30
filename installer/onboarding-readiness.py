#!/usr/bin/env python3
"""Offline onboarding readiness adapter. Never executes installation."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_plan():
    spec = importlib.util.spec_from_file_location(
        "patch_onboarding_beta_plan", HERE / "beta-install-plan.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pending(reason, next_action):
    return {
        "status": "pending",
        "ready_for_isolated_test": False,
        "ready_for_production": False,
        "checks": [],
        "failed_checks": [],
        "blockers": [reason],
        "next_action": next_action,
        "changes_made": False,
        "network_requests_made": False,
    }


def evaluate(*, role, server=None, ca_cert=None,
             certificate_mode="existing-ca", package=None,
             os_release="/etc/os-release"):
    if role == "server":
        return pending(
            "Server installation readiness is not implemented",
            "Implement and verify the server preflight workflow",
        )

    if role != "agent":
        raise ValueError("Unsupported onboarding role")

    if certificate_mode == "generate-test-ca":
        return pending(
            "Disposable test CA has not been generated",
            "Generate a disposable test CA using the existing "
            "certificate tooling, then rerun readiness with "
            "--certificate-mode existing-ca and --ca-cert",
        )

    if certificate_mode != "existing-ca":
        raise ValueError("Unsupported certificate mode")

    if not ca_cert:
        return pending(
            "CA certificate path is missing",
            "Supply an existing CA certificate path",
        )

    plan = load_plan().plan(
        server=server,
        ca_cert=ca_cert,
        package=Path(package) if package else None,
        os_release=os_release,
    )

    ready = bool(plan["ready_for_isolated_test"])
    checks = list(plan["checks"])
    failed = list(plan["failed_checks"])

    # The existing planner includes intentional production gates.
    # Those gates must remain visible, but they do not automatically
    # disqualify an otherwise ready disposable test.
    return {
        "status": "isolated-test-ready" if ready else "blocked",
        "ready_for_isolated_test": ready,
        "ready_for_production": False,
        "checks": checks,
        "failed_checks": failed,
        "blockers": [
            item["detail"] for item in checks
            if not item["ok"] and item["name"] not in (
                "production_installer", "end_to_end_enrollment"
            )
        ],
        "next_action": (
            "Review an explicit disposable staging target; "
            "onboarding will not execute staging"
            if ready else
            "Resolve preflight failures and rerun readiness"
        ),
        "changes_made": False,
        "network_requests_made": False,
    }
