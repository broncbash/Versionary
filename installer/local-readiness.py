#!/usr/bin/env python3
"""Run offline disposable verification locally; never deploy."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evidence_gate():
    path = ROOT / "installer/offline-evidence-gate.py"
    spec = importlib.util.spec_from_file_location("local_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_command(command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)


def verify(runner=run_command):
    commands = (
        ("package", [sys.executable, "installer/build-agent-package.py"]),
        ("tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"]),
        ("beta", [sys.executable, "installer/beta-selftest.py", "--protocol-check"]),
        ("matrix", [sys.executable, "installer/recovery-fault-matrix.py", "--exhaustive", "--summary"]),
    )
    outputs = {}
    issues = []
    for name, command in commands:
        try:
            output = runner(command)
            outputs[name] = output
            if output.returncode != 0:
                issues.append(name + " failed")
                break
        except (OSError, subprocess.TimeoutExpired) as error:
            issues.append(name + ": " + str(error))
            break
    count = None
    if not issues:
        try:
            log = outputs["tests"].stderr + "\n" + outputs["tests"].stdout
            match = re.search(r"^Ran ([0-9]+) tests? in ", log, re.MULTILINE)
            if match is None or re.search(r"^OK$", log, re.MULTILINE) is None:
                raise ValueError("Missing test success markers")
            count = int(match.group(1))
            evidence = evidence_gate().inspect(
                json.loads(outputs["beta"].stdout),
                json.loads(outputs["matrix"].stdout), count)
            issues.extend(evidence["issues"])
        except (ValueError, TypeError, KeyError) as error:
            issues.append("Evidence invalid: " + str(error))
    return {"status": "passed" if not issues else "failed",
            "scope": "offline-disposable-only", "regression_tests": count,
            "completed_steps": list(outputs), "issues": issues,
            "production_approved": False, "deployment_permitted": False,
            "hosted_ci_used": False}


def main():
    report = verify()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
