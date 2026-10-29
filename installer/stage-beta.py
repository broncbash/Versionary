#!/usr/bin/env python3
"""Stage a persistent, inert beta agent filesystem in an explicit test root.

Never targets /, starts services, registers agents, or contacts a server.
"""
import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE / "dist/arby-patch-agent.tar.gz"


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def stage(*, root, server, ca_cert, package=DEFAULT_PACKAGE):
    root = Path(root).absolute()
    if root == Path("/") or root.is_symlink() or not root.is_dir():
        raise ValueError("A pre-existing non-root test directory is required")
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o022):
        raise ValueError("Test root has unsafe ownership or permissions")
    # Validate all external inputs before any installer changes the test root.
    config = module("setup-config.py", "arby_beta_config")
    config.validate_config({"server": server, "ca_cert": "/etc/arby-patch-agent/ca.crt"})
    ca = module("install-ca.py", "arby_beta_ca")
    ca_source = Path(ca_cert)
    if ca_source.is_symlink() or not ca_source.is_file():
        raise ValueError("CA source must be a regular file")
    ca.validate_ca(ca_source.read_bytes())
    package = Path(package).absolute()
    validator = module("validate-package.py", "arby_beta_validator")
    if package.is_symlink() or not package.is_file():
        raise ValueError("Agent package must be a regular file")
    validator.validate(package)

    for script, args in (
        ("install-files.py", [str(package), "--root", str(root)]),
        ("install-ca.py", [str(ca_source), "--root", str(root)]),
        ("setup-config.py", ["--root", str(root), "--server", server]),
        ("install-systemd.py", ["--root", str(root)]),
        ("audit-test-install.py", ["--root", str(root), "--package", str(package)]),
    ):
        subprocess.run([sys.executable, str(HERE / script), *args], check=True,
                       stdout=subprocess.DEVNULL)
    return {
        "status": "staged",
        "mode": "isolated-beta",
        "root": str(root),
        "production_installed": False,
        "systemd_started": False,
        "agent_enrolled": False,
        "network_requests_made": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(stage(root=args.root, server=args.server,
                               ca_cert=args.ca_cert, package=args.package), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] Beta staging failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
