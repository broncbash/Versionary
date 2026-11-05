#!/usr/bin/env python3
"""Read-only, offline deployment readiness report for an agent candidate.

Does not install, enroll, contact servers, or enable services.
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_preflight():
    spec = importlib.util.spec_from_file_location(
        "arby_deployment_agent_preflight", HERE / "agent-preflight.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(*, server, ca_cert, package=None, os_release="/etc/os-release"):
    preflight = load_preflight().inspect(
        server=server, ca_cert=ca_cert, package=package,
        os_release=os_release,
    )
    checks = list(preflight["checks"])
    # The current shell installer intentionally rejects --install.
    # Keep the deployment gate closed until the actual production path is
    # implemented, reviewed, and separately authorized.
    checks.append({
        "name": "production_installer",
        "ok": False,
        "detail": "Production --install is intentionally disabled",
    })
    checks.append({
        "name": "end_to_end_enrollment",
        "ok": False,
        "detail": "Live enrollment and server reporting require an approved test",
    })
    return {
        "ready_for_production": False,
        "ready_for_isolated_test": bool(preflight["ready"]),
        "mode": "read-only",
        "changes_made": False,
        "network_requests_made": False,
        "checks": checks,
        "next_step": (
            "Complete isolated installation and approved end-to-end test "
            "before enabling production deployment"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--os-release", default="/etc/os-release")
    args = parser.parse_args(argv)
    result = report(
        server=args.server, ca_cert=args.ca_cert,
        package=args.package, os_release=args.os_release,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["ready_for_isolated_test"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
