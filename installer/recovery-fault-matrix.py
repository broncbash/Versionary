#!/usr/bin/env python3
"""Offline fault-matrix runner for Patch Command's disposable recovery trial.

Runs subprocess-based trials with private temporary roots. No production paths,
network calls, agent enrollment, service control, or hosted CI.
"""
import argparse
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "restart-recovery-trial.py"


def load_trial():
    spec = importlib.util.spec_from_file_location("patch_recovery_matrix_trial", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cases(parts, exhaustive=False):
    """Deterministic, unique cases; include every switch/recovery combination."""
    result = [("switch", name, None, None) for name in parts]
    result += [("recovery", switch, recovery, None)
               for switch in parts for recovery in parts]
    tamper = ("journal", "backup", "active", "journal_symlink",
              "backup_symlink", "active_symlink", "restore_symlink")
    result += [("tamper", "ca", None, mode) for mode in tamper]
    if exhaustive:
        result += [("tamper", switch, None, mode)
                   for switch in parts for mode in tamper if switch != "ca"]
    return result


def evaluate(trial, case):
    category, switch, recovery, tamper = case
    observed = trial.run(switch, tamper=tamper, recover_stop_at=recovery)
    expected = "refused" if category == "tamper" else "recovered"
    if observed.get("status") != expected:
        raise AssertionError("Incorrect recovery outcome")
    if observed.get("production_installed") is not False or observed.get("systemd_started") is not False:
        raise AssertionError("Production side-effect guard missing")
    if category != "tamper":
        if observed.get("agent_enrolled") is not False:
            raise AssertionError("Unexpected enrollment")
        if observed.get("external_network_requests_made") is not False:
            raise AssertionError("Unexpected external network activity")
        if observed.get("idempotent_recovery_verified") is not True:
            raise AssertionError("Idempotence not verified")
    return expected


def run(exhaustive=False, max_cases=None):
    if max_cases is not None and (type(max_cases) is not int or max_cases < 1):
        raise ValueError("max_cases must be a positive integer")
    trial = load_trial()
    selected = cases(trial.PARTS, exhaustive=exhaustive)
    if max_cases is not None:
        selected = selected[:max_cases]
    results = []
    for category, switch, recovery, tamper in selected:
        item = {"category": category, "switch": switch,
                "recovery": recovery, "tamper": tamper}
        started = time.monotonic()
        try:
            item["outcome"] = evaluate(trial, (category, switch, recovery, tamper))
            item["passed"] = True
        except Exception as exc:
            item["passed"] = False
            item["error"] = type(exc).__name__ + ": " + str(exc)
        item["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        results.append(item)
    failures = sum(not item["passed"] for item in results)
    return {"status": "passed" if failures == 0 else "failed",
            "mode": "offline-disposable-recovery-fault-matrix",
            "exhaustive": exhaustive, "cases": len(results),
            "passed": len(results) - failures, "failed": failures,
            "results": results, "production_installed": False,
            "systemd_started": False, "agent_enrolled": False,
            "external_network_requests_made": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--summary", action="store_true",
                        help="Print counts only; exit nonzero on failure")
    args = parser.parse_args(argv)
    if args.max_cases is not None and args.max_cases < 1:
        parser.error("--max-cases must be positive")
    report = run(args.exhaustive, args.max_cases)
    if args.summary:
        report = {key: value for key, value in report.items() if key != "results"}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
