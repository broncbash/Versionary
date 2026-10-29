#!/usr/bin/env python3
"""Read-only agent installation readiness report.

This command never writes files, installs packages, runs systemctl, contacts a
server, or changes the host. Production installation remains disabled.
"""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.config import validate_config

VALIDATOR = ROOT / "installer" / "validate-package.py"
spec = importlib.util.spec_from_file_location("agent_package_validator_preflight", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

DEFAULT_PACKAGE = ROOT / "installer/dist/arby-patch-agent.tar.gz"


def inspect(*, server=None, ca_cert=None, package=None, os_release="/etc/os-release"):
    checks = []
    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        release = Path(os_release).read_text(encoding="utf-8")
        distro = next((line.split("=", 1)[1].strip().strip('"')
                       for line in release.splitlines() if line.startswith("ID=")), None)
    except OSError:
        distro = None
    check("supported_os", distro in ("arch", "debian"), "Arch Linux or Debian required")
    check("python", sys.version_info >= (3, 11), "Python 3.11+ required")
    check("systemctl", shutil.which("systemctl") is not None, "systemctl available")
    check("cryptography", _has_crypto(), "Ed25519 cryptography available")
    check("scanner", shutil.which("checkupdates" if distro == "arch" else "apt") is not None
          if distro in ("arch", "debian") else False, "Read-only package scanner available")

    valid_server = False
    if server:
        try:
            validate_config({"server": server, "ca_cert": "/etc/arby-patch-agent/ca.crt"})
            valid_server = True
        except (ValueError, TypeError, KeyError):
            pass
    check("https_server", valid_server, "Valid HTTPS server origin provided")

    trusted_ca = False
    if ca_cert:
        try:
            p = Path(ca_cert)
            info = p.lstat()
            trusted_ca = (stat.S_ISREG(info.st_mode) and
                          p.read_bytes().startswith(b"-----BEGIN CERTIFICATE-----") and
                          p.stat().st_size <= 1024 * 1024)
        except (OSError, ValueError):
            pass
    check("ca_certificate", trusted_ca, "Explicit readable PEM CA certificate supplied")

    pkg = Path(package) if package is not None else DEFAULT_PACKAGE
    valid_package = False
    try:
        valid_package = pkg.is_file() and not pkg.is_symlink() and validator.validate(pkg) > 0
    except (OSError, ValueError, Exception) as exc:
        # Validator may raise tarfile.TarError for malformed archives.
        valid_package = False
    check("agent_package", valid_package, "Validated agent distribution archive available")
    return {"ready": all(item["ok"] for item in checks), "mode": "read-only",
            "production_install_enabled": False, "changes_made": False,
            "platform": distro, "checks": checks}


def _has_crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return Ed25519PrivateKey is not None
    except ImportError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", help="HTTPS server origin")
    parser.add_argument("--ca-cert", help="Existing trusted CA certificate")
    parser.add_argument("--package", help="Validated agent archive")
    parser.add_argument("--os-release", default="/etc/os-release",
                        help="OS release file for isolated testing")
    args = parser.parse_args(argv)
    result = inspect(server=args.server, ca_cert=args.ca_cert,
                     package=args.package, os_release=args.os_release)
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
