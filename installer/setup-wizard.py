#!/usr/bin/env python3
"""Unified, read-only Patch Command installation planner.

No filesystem mutations, network requests, service changes, or enrollment.
Production installation is deliberately unavailable.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def load_module(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_server(value):
    if not value:
        raise ValueError("An HTTPS server address is required")

    parsed = urlsplit(value)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.netloc
        or "@" in parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or any(char.isspace() for char in value)
        or "\\" in value
    ):
        raise ValueError("Server must be an HTTPS origin without credentials, paths, or query parameters")

    try:
        port = parsed.port
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("Invalid HTTPS address") from exc

    if not hostname or not parsed.netloc:
        raise ValueError("Invalid HTTPS hostname")

    if port is not None and not (1 <= port <= 65535):
        raise ValueError("Invalid HTTPS port")

    return value.rstrip("/")


def build_plan(role, server=None, ca_cert=None, package=None, os_release="/etc/os-release"):
    if role not in ("agent", "server"):
        raise ValueError("Role must be agent or server")

    if role == "server":
        return {
            "product": "Patch Command",
            "role": "server",
            "mode": "read-only-planning",
            "status": "not-yet-supported",
            "ready_for_isolated_test": False,
            "ready_for_production": False,
            "changes_made": False,
            "network_requests_made": False,
            "message": "Server installation orchestration is not implemented yet.",
            "planned_phases": [
                "Validate platform and dependencies",
                "Configure server URL and TLS certificates",
                "Prepare isolated installation target",
                "Stage server application and inactive service",
                "Verify rollback and recovery",
                "Review before enabling production installation",
            ],
        }

    server = validate_server(server)

    if not ca_cert:
        raise ValueError("Agent planning requires --ca-cert")

    existing = load_module(
        "beta-install-plan.py",
        "patch_wizard_beta_plan",
    )

    result = existing.plan(
        server=server,
        ca_cert=ca_cert,
        package=Path(package) if package else None,
        os_release=os_release,
    )

    result["role"] = "agent"
    result["wizard_version"] = 1
    result["server"] = server
    result["ca_certificate"] = str(ca_cert)
    result["production_install_enabled"] = False
    result["enrollment_enabled"] = False

    return result


def interactive_inputs(args):
    if not sys.stdin.isatty():
        raise ValueError("Interactive mode requires a terminal")

    if not args.role:
        args.role = input("Install role [agent/server]: ").strip().lower()

    if args.role == "agent":
        if not args.server:
            args.server = input("Patch Command HTTPS server: ").strip()
        if not args.ca_cert:
            args.ca_cert = input("Trusted CA PEM file: ").strip()

    return args


def render_text(result):
    lines = [
        "PATCH COMMAND — INSTALLATION PLAN",
        "=" * 40,
        f"Role: {result['role']}",
        f"Status: {result['status']}",
        f"Mode: {result['mode']}",
        "Production installation: DISABLED",
        "Changes made: NO",
        "Network requests: NO",
    ]

    if result["role"] == "agent":
        lines.append(f"Server: {result['server']}")

        for item in result["checks"]:
            label = "PASS" if item["ok"] else "FAIL"
            lines.append(f"[{label}] {item['name']}: {item['detail']}")

        if result["failed_checks"]:
            lines.append("Failed checks: " + ", ".join(result["failed_checks"]))
    else:
        lines.append(result["message"])

    lines.append("")
    lines.append("This command is a read-only plan. Nothing was installed.")

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interactive or scriptable Patch Command installation planner"
    )
    parser.add_argument("--role", choices=("agent", "server"))
    parser.add_argument("--server")
    parser.add_argument("--ca-cert")
    parser.add_argument("--package")
    parser.add_argument("--os-release", default="/etc/os-release")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Reserved for future use; production installation is disabled",
    )

    args = parser.parse_args(argv)

    if args.install:
        parser.error("Production installation is disabled")

    try:
        if args.interactive:
            args = interactive_inputs(args)

        if not args.role:
            raise ValueError("Specify --role or use --interactive")

        result = build_plan(
            role=args.role,
            server=args.server,
            ca_cert=args.ca_cert,
            package=args.package,
            os_release=args.os_release,
        )
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result))

    return 0 if result["ready_for_isolated_test"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
