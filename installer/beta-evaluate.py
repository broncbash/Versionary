#!/usr/bin/env python3
"""Offline beta evaluation entry point.

Runs disposable staging and optional loopback HTTPS acceptance. It never
installs software on the host, enables services, or enrolls an agent.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(*, protocol_check=False, smoke_scan=False):
    selftest = load("beta-selftest.py", "patch_command_beta_selftest")
    result = selftest.run(protocol_check=protocol_check, smoke_scan=smoke_scan)
    if result["status"] != "passed" or result["production_installed"] or result["systemd_started"]:
        raise RuntimeError("Disposable beta verification did not pass safely")
    return {
        "product": "Versionary",
        "evaluation": "isolated-agent-beta",
        "status": "passed",
        "production_ready": False,
        "host_modified": False,
        "agent_enrolled": False,
        "next_step": "Review deployment readiness and authorize a separate beta installation",
        "verification": result,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-check", action="store_true",
                        help="Verify enrollment and reporting against a disposable loopback HTTPS server")
    parser.add_argument("--smoke-scan", action="store_true",
                        help="Run a read-only local package scan in the staged agent")
    args = parser.parse_args(argv)
    try:
        report = evaluate(protocol_check=args.protocol_check, smoke_scan=args.smoke_scan)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Beta evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
