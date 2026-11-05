#!/usr/bin/env python3
"""Read-only Versionary beta deployment readiness report.

Never installs, modifies a target, starts services, or enrolls.
Supports an isolated root or an explicit read-only system audit.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import stat
import sys

HERE = Path(__file__).resolve().parent

def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024), b""
        ):
            h.update(chunk)
    return h.hexdigest()

def check_root(root, allow_system=False):
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("Absolute root required")
    if root.is_symlink():
        raise ValueError("Symlinked root forbidden")
    if root == Path("/") and not allow_system:
        raise ValueError(
            "System audit requires --audit-system"
        )
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Root must be a directory")
    if info.st_mode & 0o022:
        raise ValueError("Unsafe root permissions")
    return root

def report(root, distribution, server, ca_cert,
           allow_system=False):
    root = check_root(root, allow_system)
    result = {
        "schema": "versionary.beta.readiness.v1",
        "root": str(root),
        "system_audit": root == Path("/"),
        "read_only": True,
        "installation_performed": False,
        "services_activated": False,
        "enrollment_performed": False,
        "production_approved": False,
        "real_system_installation_enabled": False,
        "checks": {},
        "blockers": [],
    }

    def check(name, callback):
        try:
            detail = callback()
            result["checks"][name] = {
                "status": "pass",
                "detail": detail,
            }
        except Exception as exc:
            result["checks"][name] = {
                "status": "fail",
                "reason": str(exc),
            }
            result["blockers"].append(name)

    preflight = load(
        "versionary-agent-system-preflight.py",
        "versionary86_preflight",
    )
    conflicts = load(
        "versionary-agent-system-conflicts.py",
        "versionary86_conflicts",
    )
    content = load(
        "versionary-agent-system-content.py",
        "versionary86_content",
    )

    check(
        "platform",
        lambda: {
            "linux": platform.system() == "Linux",
            "python": sys.version.split()[0],
        } if platform.system() == "Linux"
        else (_ for _ in ()).throw(
            ValueError("Linux required")
        ),
    )

    check(
        "distribution_and_trust",
        lambda: preflight.preflight(
            distribution, server, ca_cert
        ),
    )

    if result["checks"]["distribution_and_trust"][
        "status"
    ] == "pass":
        check(
            "distribution_sha256",
            lambda: digest(distribution),
        )
        check(
            "ca_sha256",
            lambda: digest(ca_cert),
        )

    check(
        "filesystem_conflicts",
        lambda: conflicts.inspect(root),
    )

    def inspect_content():
        payloads = content.expected_payloads(
            distribution, server, ca_cert
        )
        return content.inspect_existing(root, payloads)

    if result["checks"]["distribution_and_trust"][
        "status"
    ] == "pass":
        check("existing_content", inspect_content)

    if root != Path("/"):
        gate = load(
            "versionary-agent-beta-system-fresh-gate.py",
            "versionary86_gate",
        )
        check("fresh_install_gate", lambda: gate.inspect(root))
    else:
        result["blockers"].append(
            "real_system_installation_not_implemented"
        )

    result["ready_for_review"] = (
        len(result["blockers"]) == 0
    )
    result["deployment_authorized"] = False
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    parser.add_argument(
        "--audit-system", action="store_true"
    )
    args = parser.parse_args()

    try:
        result = report(
            args.root, args.distribution,
            args.server, args.ca_cert,
            allow_system=args.audit_system,
        )
    except (OSError, ValueError) as exc:
        print("[STOP]", exc, file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["ready_for_review"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
