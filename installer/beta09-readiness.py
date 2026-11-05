#!/usr/bin/env python3
"""Beta 0.9 clean-checkout readiness audit. No production deployment."""

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPENDENCIES = ("uvicorn", "fastapi", "cryptography")


def audit(python):
    python = Path(python).absolute()

    if not python.is_file():
        raise RuntimeError(f"Python interpreter missing: {python}")

    for module in DEPENDENCIES:
        check = subprocess.run(
            [str(python), "-c",
             f"import importlib.util; assert importlib.util.find_spec({module!r})"],
            capture_output=True, text=True,
        )
        if check.returncode:
            raise RuntimeError(
                f"Missing {module} in {python}. "
                "Select the project virtual environment with --python."
            )

    with tempfile.TemporaryDirectory(prefix="versionary-beta09-audit-") as tmp:
        checkout = Path(tmp) / "checkout"

        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if head.returncode:
            raise RuntimeError(f"Cannot resolve HEAD: {head.stderr}")
        commit = head.stdout.strip()

        clone = subprocess.run(
            ["git", "clone", "--quiet", "--local", "--no-hardlinks",
             "--no-checkout", str(ROOT), str(checkout)],
            capture_output=True, text=True,
        )
        if clone.returncode:
            raise RuntimeError(f"Clone failed: {clone.stderr}")

        checkout_result = subprocess.run(
            ["git", "checkout", "--quiet", "--detach", commit],
            cwd=checkout, capture_output=True, text=True,
        )
        if checkout_result.returncode:
            raise RuntimeError(
                f"Checkout failed: {checkout_result.stderr}"
            )

        checks = [
            ("isolated-staging",
             [str(python), "installer/beta-selftest.py"]),
            ("https-protocol",
             [str(python), "installer/beta-selftest.py", "--protocol-check"]),
            ("recovery-security",
             [str(python), "-m", "unittest", "discover",
              "-s", "tests", "-p", "test_beta09_recovery_security.py", "-q"]),
        ]

        results = {}
        for name, command in checks:
            result = subprocess.run(
                command, cwd=checkout, capture_output=True,
                text=True, timeout=180,
            )
            results[name] = {
                "passed": result.returncode == 0,
                "exit_code": result.returncode,
                "details": (result.stderr or result.stdout)[-2000:]
                if result.returncode else "",
            }

        return {
            "status": "passed" if all(
                item["passed"] for item in results.values()
            ) else "failed",
            "python": str(python),
            "checks": results,
            "production_deployed": False,
            "temporary_checkout_removed": True,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python", default=sys.executable,
        help="Python interpreter containing project dependencies",
    )
    args = parser.parse_args()

    try:
        result = audit(args.python)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"Readiness audit failed: {exc}\\n")

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
