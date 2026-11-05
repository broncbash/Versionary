#!/usr/bin/env python3
"""Disposable agent install trial with automatic workspace cleanup.

Never targets a live installation. No service activation or enrollment.
"""
import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial(*, server, ca_cert, package=None):
    staging = load("stage-beta.py", "patch_command_stage_trial")
    kwargs = {"server": server, "ca_cert": ca_cert}
    if package is not None:
        kwargs["package"] = package
    # TemporaryDirectory creates a private new root, not an existing host root.
    # Its cleanup runs even when staging or verification raises an exception.
    with tempfile.TemporaryDirectory(prefix="versionary-trial-") as directory:
        root = Path(directory)
        staged = staging.stage(root=root, **kwargs)
        if staged["status"] != "staged":
            raise RuntimeError("Agent staging did not complete")
        verified = staging.stage(root=root, verify_only=True, **kwargs)
        if verified["status"] != "verified" or verified["changes_made"]:
            raise RuntimeError("Agent staging integrity check failed")
        return {
            "product": "Versionary",
            "status": "passed",
            "mode": "disposable-install-trial",
            "staging": "verified",
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
            "external_network_requests_made": False,
            "temporary_workspace_cleaned": True,
            "rollback_scope": "disposable workspace only",
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--package")
    args = parser.parse_args(argv)
    try:
        report = trial(server=args.server, ca_cert=args.ca_cert, package=args.package)
    except (OSError, ValueError, RuntimeError, __import__("subprocess").CalledProcessError) as exc:
        print(f"Disposable trial failed: {exc}", file=__import__("sys").stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
