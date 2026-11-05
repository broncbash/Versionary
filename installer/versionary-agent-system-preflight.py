#!/usr/bin/env python3
"""Non-installing preflight for controlled Versionary agent beta deployment."""

import argparse
import importlib.util
import os
import platform
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_helper(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_regular_file(path, label, max_size):
    path = Path(path)
    info = path.lstat()

    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} must be a regular file")

    if info.st_size <= 0 or info.st_size > max_size:
        raise ValueError(f"{label} has invalid size")

    if info.st_mode & 0o022:
        raise ValueError(f"{label} is writable by group or others")

    return path


def validate_platform():
    if platform.system() != "Linux":
        raise ValueError("Linux is required")

    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11 or newer is required")

    try:
        import cryptography
    except ImportError as exc:
        raise ValueError(
            "Python cryptography dependency is missing"
        ) from exc

    return cryptography.__version__


def preflight(distribution, server, ca_cert):
    crypto_version = validate_platform()

    distribution = validate_regular_file(
        distribution, "Agent distribution", 16 * 1024 * 1024
    )

    ca_cert = validate_regular_file(
        ca_cert, "CA certificate", 1024 * 1024
    )

    cli = load_helper(
        "install-agent-cli.py",
        "versionary_beta_cli_preflight",
    )
    config = load_helper(
        "../agent/config.py",
        "versionary_beta_config_preflight",
    )
    ca = load_helper(
        "install-ca.py",
        "versionary_beta_ca_preflight",
    )

    cli.verified_cli(distribution)
    config.validate_server(server)
    ca.validate_ca(ca_cert.read_bytes())

    return {
        "python": sys.version.split()[0],
        "cryptography": crypto_version,
        "server": server,
        "distribution": str(distribution),
        "ca_cert": str(ca_cert),
        "production_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    args = parser.parse_args()

    try:
        result = preflight(
            args.distribution,
            args.server,
            args.ca_cert,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print("[FAIL]", exc, file=sys.stderr)
        return 1

    print("[PASS] Versionary system beta preflight")
    print("[PASS] Python:", result["python"])
    print("[PASS] Cryptography:", result["cryptography"])
    print("[PASS] Distribution verified")
    print("[PASS] Server URL validated")
    print("[PASS] CA certificate validated")
    print("[PASS] No installation performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
