#!/usr/bin/env python3
"""Integrated isolated Versionary beta installation.

Installs the complete 13-module offline distribution.
A durable recovery marker blocks retries after interruption.
Never installs into / or activates/enrolls an agent.
"""

import argparse
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUTHORIZATION = "I_AUTHORIZE_ISOLATED_VERSIONARY_BETA_INSTALL"
MARKER = ".versionary-full-install-recovery.json"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_root(root):
    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary89_coordinator",
    )
    root = coordinator.validate_root(root)

    if root.resolve() == Path("/"):
        raise ValueError("Real-system installation disabled")

    return root


def marker_path(root):
    return Path(root) / MARKER


def read_marker(root):
    root = validate_root(root)
    path = marker_path(root)

    try:
        info = path.lstat()
    except FileNotFoundError:
        return None

    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_nlink != 1
        or info.st_mode & 0o077
        or info.st_size <= 0
        or info.st_size > 65536
    ):
        raise RuntimeError("Unsafe recovery marker")

    data = json.loads(path.read_bytes())

    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or data.get("status") != "installing"
        or data.get("scope") != "isolated-full-agent"
    ):
        raise RuntimeError("Unsupported recovery marker")

    return data


def sync_dir(root):
    fd = os.open(
        root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_marker(root):
    root = validate_root(root)
    data = {
        "version": 1,
        "status": "installing",
        "scope": "isolated-full-agent",
        "automatic_rollback": False,
    }

    fd = os.open(
        marker_path(root),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL |
        getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )

    with os.fdopen(fd, "wb") as stream:
        stream.write(
            (json.dumps(data, sort_keys=True) + "\n").encode()
        )
        stream.flush()
        os.fsync(stream.fileno())

    sync_dir(root)
    return data


def inspect(root):
    root = validate_root(root)
    marker = read_marker(root)

    if marker is not None:
        return {
            "status": "recovery_required",
            "root": str(root),
            "marker": marker,
            "automatic_recovery": False,
        }

    return {
        "status": "clear",
        "root": str(root),
        "automatic_recovery": False,
    }


def verify_complete(root, distribution, server, ca_cert):
    root = validate_root(root)

    content = load(
        "versionary-agent-system-content.py",
        "versionary89_content",
    )
    coordinator = load(
        "versionary-agent-isolated-coordinator.py",
        "versionary89_verify_coordinator",
    )
    files = load(
        "install-files.py",
        "versionary89_files",
    )

    payloads = content.expected_payloads(
        distribution, server, ca_cert
    )

    result = content.inspect_existing(root, payloads)

    if any(value != "identical" for value in result.values()):
        raise RuntimeError("Incomplete installation payloads")

    active = root / "opt/versionary-agent/agent"

    if not active.is_symlink():
        raise RuntimeError("Active agent release missing")

    release = active.resolve(strict=True)
    releases = (
        root / "opt/versionary-agent/releases"
    ).resolve(strict=True)

    if release.parent.parent != releases:
        raise RuntimeError("Active release outside release store")

    if not release.is_dir():
        raise RuntimeError("Active release is not a directory")

    expected = files.MODULES
    actual = {
        path.name
        for path in release.iterdir()
        if path.is_file() and not path.is_symlink()
    }

    if actual != expected:
        raise RuntimeError("Agent module inventory mismatch")

    for path in release.iterdir():
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_mode & 0o022
        ):
            raise RuntimeError("Unsafe installed agent module")

    return {
        "verified_modules": len(expected),
        "verified_support_files": len(payloads),
        "services_activated": False,
        "enrollment_performed": False,
    }


def prepare(root, distribution, server, ca_cert):
    root = validate_root(root)

    if inspect(root)["status"] != "clear":
        raise RuntimeError(
            "Pending full-install recovery requires review"
        )

    durable = load(
        "versionary-agent-durable-install.py",
        "versionary89_durable",
    )

    if durable.inspect(root)["status"] != "clear":
        raise RuntimeError(
            "Pending durable recovery requires review"
        )

    fresh = load(
        "versionary-agent-beta-full-fresh-install.py",
        "versionary89_fresh",
    )

    fresh.prepare(root, distribution, server, ca_cert)

    return {
        "status": "ready_for_isolated_full_install",
        "root": str(root),
        "module_count": 13,
        "real_system_installation_enabled": False,
        "installation_performed": False,
    }


def run(root, distribution, server, ca_cert,
        execute=False, authorization=None):
    if execute and authorization != AUTHORIZATION:
        raise PermissionError(
            "Explicit isolated authorization required"
        )

    if not execute and authorization is not None:
        raise ValueError(
            "Authorization requires execution"
        )

    plan = prepare(root, distribution, server, ca_cert)

    if not execute:
        return plan

    root = validate_root(root)

    # Recheck before creating durable intent.
    prepare(root, distribution, server, ca_cert)
    create_marker(root)

    # Any exception leaves the marker for manual review.
    offline = load(
        "install-agent-offline.py",
        "versionary89_offline",
    )
    offline.install(root, distribution, server, ca_cert)

    verified = verify_complete(
        root, distribution, server, ca_cert
    )

    path = marker_path(root)
    read_marker(root)
    path.unlink()
    sync_dir(root)

    return {
        "status": "isolated_full_install_complete",
        "root": str(root),
        "installation_performed": True,
        "real_system_installation_enabled": False,
        "globally_atomic": False,
        "production_approved": False,
        **verified,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument(
        "--execute-isolated", action="store_true"
    )
    parser.add_argument("--authorize-isolated")
    args = parser.parse_args()

    try:
        if args.inspect:
            if args.execute_isolated or args.authorize_isolated:
                raise ValueError(
                    "Inspection cannot execute installation"
                )
            result = inspect(args.root)
        else:
            result = run(
                args.root,
                args.distribution,
                args.server,
                args.ca_cert,
                execute=args.execute_isolated,
                authorization=args.authorize_isolated,
            )
    except Exception as exc:
        print("[STOP]", exc, file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
