#!/usr/bin/env python3
"""Read-only offline evidence gate for disposable Versionary verification.

Consumes local JSON reports. Never runs a test, modifies a service, or approves
production deployment. Evidence is untrusted input and is strictly validated.
"""
import argparse
import json
import os
import stat
import sys
from pathlib import Path

SCHEMA = 1
REQUIRED_FLAGS = ("production_installed", "systemd_started",
                  "agent_enrolled", "external_network_requests_made")
REQUIRED_BETA = ("status", "mode", "package_built", "test_ca_generated",
                 "initial_stage", "repeat_stage", "integrity_audit",
                 "tls_protocol_check", *REQUIRED_FLAGS)
REQUIRED_MATRIX = ("status", "mode", "exhaustive", "cases", "passed", "failed",
                   *REQUIRED_FLAGS)


def load_json(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1048576:
            raise ValueError("Unsafe or oversized evidence file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(1048577)
    finally:
        os.close(fd)
    if len(raw) > 1048576:
        raise ValueError("Oversized evidence file")
    def no_duplicate(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=no_duplicate,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("Invalid JSON constant: " + value)))


def check_flags(report, failures, prefix):
    for flag in REQUIRED_FLAGS:
        if report.get(flag) is not False:
            failures.append(prefix + ": " + flag + " must be false")


def inspect(beta, matrix, tests):
    failures = []
    if not isinstance(beta, dict) or not isinstance(matrix, dict):
        raise ValueError("Evidence must be JSON objects")
    for field in REQUIRED_BETA:
        if field not in beta:
            failures.append("beta: missing " + field)
    for field in REQUIRED_MATRIX:
        if field not in matrix:
            failures.append("matrix: missing " + field)
    if beta.get("status") != "passed" or beta.get("mode") != "disposable-isolated-beta":
        failures.append("beta: invalid status or mode")
    for field in ("package_built", "test_ca_generated"):
        if beta.get(field) is not True:
            failures.append("beta: " + field + " must be true")
    for field, value in (("initial_stage", "staged"), ("repeat_stage", "staged"),
                         ("integrity_audit", "verified"), ("tls_protocol_check", "passed")):
        if beta.get(field) != value:
            failures.append("beta: " + field + " mismatch")
    if beta.get("network_requests_made") is not True:
        failures.append("beta: isolated loopback network test not evidenced")
    check_flags(beta, failures, "beta")
    if matrix.get("status") != "passed" or matrix.get("mode") != "offline-disposable-recovery-fault-matrix":
        failures.append("matrix: invalid status or mode")
    if matrix.get("exhaustive") is not True:
        failures.append("matrix: exhaustive run required")
    for field, value in (("cases", 65), ("passed", 65), ("failed", 0)):
        if type(matrix.get(field)) is not int or matrix[field] != value:
            failures.append("matrix: " + field + " mismatch")
    check_flags(matrix, failures, "matrix")
    if type(tests) is not int or tests < 716:
        failures.append("regression: at least 716 passing tests required")
    return {"schema": SCHEMA, "status": "passed" if not failures else "failed",
            "scope": "offline-disposable-evidence-only",
            "regression_tests_reported": tests,
            "recovery_cases_required": 65, "issues": failures,
            "production_approved": False, "deployment_permitted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--beta-json", required=True)
    parser.add_argument("--matrix-json", required=True)
    parser.add_argument("--tests", type=int, required=True,
                        help="Operator-reported count of passing local regression tests")
    args = parser.parse_args(argv)
    try:
        report = inspect(load_json(args.beta_json), load_json(args.matrix_json), args.tests)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        report = {"schema": SCHEMA, "status": "failed",
                  "scope": "offline-disposable-evidence-only",
                  "issues": [type(exc).__name__ + ": " + str(exc)],
                  "production_approved": False, "deployment_permitted": False}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
