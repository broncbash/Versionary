#!/usr/bin/env python3
"""Build an explicit, non-deploying agent beta installation plan.

All checks are read-only. No service, package manager, agent or server is changed.
"""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plan(*, server, ca_cert, package=None, os_release="/etc/os-release"):
    readiness = load("deployment-readiness.py", "patch_deployment_readiness").report(
        server=server, ca_cert=ca_cert, package=package, os_release=os_release
    )
    checks = readiness["checks"]
    failed = [item["name"] for item in checks if not item["ok"]]
    return {
        "product": "Versionary",
        "mode": "read-only-planning",
        "status": "isolated-test-ready" if readiness["ready_for_isolated_test"] else "blocked",
        "ready_for_isolated_test": readiness["ready_for_isolated_test"],
        "ready_for_production": False,
        "changes_made": False,
        "network_requests_made": False,
        "failed_checks": failed,
        "checks": checks,
        "required_approvals": [
            "Explicit disposable target and installation scope",
            "Review of backup and rollback procedure",
            "Explicit permission before changing any live host",
            "Separate approval of enrollment and server feature gates",
        ],
        "planned_phases": [
            {"phase": "preflight", "action": "Validate platform, tools, HTTPS CA and agent archive"},
            {"phase": "isolate", "action": "Select pre-existing safe disposable test root"},
            {"phase": "stage", "action": "Stage agent files, CA, config and inactive systemd units"},
            {"phase": "verify", "action": "Audit staged files and repeat-installation behavior"},
            {"phase": "protocol", "action": "Run disposable loopback TLS acceptance"},
            {"phase": "review", "action": "Record evidence; stop before live installation or enrollment"},
        ],
        "next_step": (
            "Use stage-beta.py only with an explicit disposable root; "
            "production installation and enrollment remain disabled"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--os-release", default="/etc/os-release")
    args = parser.parse_args(argv)
    result = plan(server=args.server, ca_cert=args.ca_cert,
                  package=args.package, os_release=args.os_release)
    print(json.dumps(result, indent=2))
    return 0 if result["ready_for_isolated_test"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
