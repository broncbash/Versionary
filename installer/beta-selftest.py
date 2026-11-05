#!/usr/bin/env python3
"""One-command disposable beta installation self-test; never deploys.

Builds the distribution, creates a private throwaway CA and filesystem root,
stages the agent twice, and verifies the staged result. All artifacts are
removed when the command exits. No server connections or systemd actions.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*, smoke_scan=False, protocol_check=False):
    builder = load("build-agent-package.py", "beta_selftest_builder")
    certs = load("generate-certificates.py", "beta_selftest_certs")
    staging = load("stage-beta.py", "beta_selftest_staging")
    with tempfile.TemporaryDirectory(prefix="arby-beta-selftest-") as tmp:
        base = Path(tmp)
        package = builder.build(base / "agent.tar.gz")
        cert_dir = base / "certificates"
        certs.generate("127.0.0.1", cert_dir)
        root = base / "isolated-root"
        root.mkdir(mode=0o700)
        inputs = dict(root=root, server="https://127.0.0.1:8443",
                      ca_cert=cert_dir / "ca.crt", package=package)
        first = staging.stage(**inputs)
        second = staging.stage(**inputs)
        verified = staging.stage(**inputs, verify_only=True, smoke_scan=smoke_scan)
        if (first["status"], second["status"], verified["status"]) != (
                "staged", "staged", "verified"):
            raise RuntimeError("Beta self-test did not complete")
        if any(item.get("production_installed") or item.get("systemd_started")
               or item.get("agent_enrolled") or item.get("network_requests_made")
               for item in (first, second, verified)):
            raise RuntimeError("Beta self-test violated isolation guarantees")
        if verified["changes_made"]:
            raise RuntimeError("Read-only verification modified staged files")
        protocol_status = "not-requested"
        if protocol_check:
            # Run the real HTTPS integration suite in a separate process. It
            # creates its own loopback-only TLS server and disposable database.
            result = subprocess.run(
                [sys.executable, "-B", "-m", "unittest",
                 "tests.test_beta_tls_journey", "-q"],
                cwd=str(HERE.parent), capture_output=True, text=True,
                timeout=120, check=False,
            )
            if result.returncode:
                raise RuntimeError(
                    "Real TLS protocol check failed: " +
                    (result.stderr or result.stdout)[-2000:])
            protocol_status = "passed"
        return {
            "status": "passed",
            "mode": "disposable-isolated-beta",
            "package_built": True,
            "test_ca_generated": True,
            "initial_stage": first["status"],
            "repeat_stage": second["status"],
            "integrity_audit": verified["status"],
            "scan_status": verified["scan_status"],
            "tls_protocol_check": protocol_status,
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
            "network_requests_made": bool(protocol_check),
            "external_network_requests_made": False,
            "artifacts_retained": False,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-scan", action="store_true",
                        help="Opt in to a read-only local package-manager scan")
    parser.add_argument("--protocol-check", action="store_true",
                        help="Run disposable real-HTTPS enrollment/reporting tests")
    args = parser.parse_args(argv)
    try:
        result = run(smoke_scan=args.smoke_scan,
                     protocol_check=args.protocol_check)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f"Beta self-test failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
