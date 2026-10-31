#!/usr/bin/env python3
"""In-memory model of coordinated asset switching and recovery.

This tool never accesses an installation root, writes files or starts services.
"""
import argparse
import hashlib
import json

ASSETS = ("release", "config", "ca", "service", "timer")
STEPS = ("prepared",) + ASSETS + ("verified",)


def checksum(value):
    return hashlib.sha256(value.encode()).hexdigest()


def simulate(fail_after=None):
    if fail_after is not None and fail_after not in STEPS:
        raise ValueError("Unknown fault checkpoint")
    before = {key: "previous:" + key for key in ASSETS}
    candidate = {key: "candidate:" + key for key in ASSETS}
    current = before.copy()
    journal = []
    def record(state):
        journal.append({"state": state, "observed": {
            key: checksum(value) for key, value in current.items()}})
        if state == fail_after:
            raise RuntimeError("Injected failure at " + state)
    failure = None
    try:
        record("prepared")
        for key in ASSETS:
            current[key] = candidate[key]
            record(key)
        record("verified")
    except RuntimeError as exc:
        failure = str(exc)
        if journal[-1]["observed"] != {key: checksum(value) for key, value in current.items()}:
            raise ValueError("Simulated journal mismatch")
        for key in reversed(ASSETS):
            current[key] = before[key]
        journal.append({"state": "recovered", "observed": {
            key: checksum(value) for key, value in current.items()}})
    expected = before if failure else candidate
    if current != expected:
        raise ValueError("Simulated final generation mismatch")
    return {"product": "Versionary", "mode": "in-memory-transaction-model",
            "status": "recovered" if failure else "verified",
            "injected_failure": failure, "journal": journal,
            "recovery_verified": bool(failure), "production_installed": False,
            "existing_files_modified": False, "systemd_started": False,
            "agent_enrolled": False, "external_network_requests_made": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-after", choices=STEPS)
    args = parser.parse_args(argv)
    print(json.dumps(simulate(args.fail_after), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
