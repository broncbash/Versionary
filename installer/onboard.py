#!/usr/bin/env python3
"""Unified, non-deploying Patch Command onboarding interface."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_preview():
    path = HERE / "installation-preview.py"
    spec = importlib.util.spec_from_file_location(
        "patch_command_installation_preview", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_readiness():
    path = HERE / "onboarding-readiness.py"
    spec = importlib.util.spec_from_file_location(
        "patch_command_onboarding_readiness", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prompt_value(label, default=None):
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def collect_interactive(args):
    print("\nPATCH COMMAND — UNIFIED ONBOARDING")
    print("Planning only. No installation will occur.\n")

    role = args.role or prompt_value("Installation role (agent/server)", "agent")

    if role not in ("agent", "server"):
        raise ValueError("Role must be agent or server")

    args.role = role

    if role == "agent":
        args.server = args.server or prompt_value(
            "Patch Command HTTPS server URL"
        )

        if not args.certificate_mode:
            choice = prompt_value(
                "Certificate mode (existing-ca/generate-test-ca)",
                "existing-ca",
            )
            args.certificate_mode = choice

        if args.certificate_mode == "existing-ca":
            args.ca_cert = args.ca_cert or prompt_value(
                "Trusted CA certificate path"
            )

    return args


def build_onboarding(
    *,
    role,
    server=None,
    ca_cert=None,
    certificate_mode=None,
    target="disposable",
    package=None,
    os_release="/etc/os-release",
):
    preview_module = load_preview()

    if certificate_mode is None:
        certificate_mode = "existing-ca"

    manifest = preview_module.create_preview(
        role=role,
        server=server,
        ca_cert=ca_cert,
        certificate_mode=certificate_mode,
        target=target,
    )

    supported = manifest["status"] == "preview-only"

    readiness = load_readiness().evaluate(
        role=role,
        server=server,
        ca_cert=ca_cert,
        certificate_mode=certificate_mode,
        package=package,
        os_release=os_release,
    )

    return {
        "schema_version": 1,
        "product": "Patch Command",
        "workflow": "unified-onboarding",
        "status": "preview-ready" if supported else "not-implemented",
        "role": role,
        "manifest": manifest,
        "readiness": readiness,
        "review": {
            "required": True,
            "completed": False,
            "meaning": "Preview acknowledgment only",
        },
        "execution": {
            "available": False,
            "performed": False,
            "installation_enabled": False,
            "enrollment_enabled": False,
            "network_requests_made": False,
            "changes_made": False,
        },
    }


def acknowledge(result):
    """Record acknowledgment in the returned result; do not execute."""
    if result["status"] != "preview-ready":
        raise ValueError("Unsupported role cannot be acknowledged")

    result["review"]["completed"] = True
    return result


def render_text(result):
    manifest = result["manifest"]
    lines = [
        "PATCH COMMAND — ONBOARDING",
        "=" * 40,
        f"Role: {result['role']}",
        f"Status: {result['status']}",
        f"Target: {manifest['target']}",
        f"Certificate mode: {manifest['certificate']['mode']}",
        "",
        "CONFIGURATION",
    ]

    for key, value in manifest["configuration"].items():
        lines.append(f"  {key}: {value}")

    lines.append("")
    lines.append("PROPOSED ARTIFACTS")

    if not manifest["artifacts"]:
        lines.append("  None — installer not implemented")

    for item in manifest["artifacts"]:
        lines.append(f"  {item['path']}")

    lines.extend([
        "",
        "READINESS",
        f"  Status: {result['readiness']['status']}",
        f"  Isolated test ready: "
        f"{result['readiness']['ready_for_isolated_test']}",
        f"  Next action: {result['readiness']['next_action']}",
        "",
        "SAFETY",
        "  Production installation: DISABLED",
        "  Service activation: DISABLED",
        "  Agent enrollment: DISABLED",
        "  Network requests: DISABLED",
        "  Changes made: NONE",
        "",
        "Acknowledgment does not install anything.",
    ])

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("agent", "server"))
    parser.add_argument("--server")
    parser.add_argument("--ca-cert")
    parser.add_argument(
        "--certificate-mode",
        choices=("existing-ca", "generate-test-ca"),
    )
    parser.add_argument("--target", default="disposable")
    parser.add_argument("--package")
    parser.add_argument("--os-release", default="/etc/os-release")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--acknowledge-preview", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")

    args = parser.parse_args(argv)

    try:
        if args.interactive:
            if args.format == "json":
                raise ValueError(
                    "Interactive prompts cannot be combined with JSON output"
                )
            args = collect_interactive(args)

        if not args.role:
            raise ValueError(
                "Specify --role or use --interactive"
            )

        result = build_onboarding(
            role=args.role,
            server=args.server,
            ca_cert=args.ca_cert,
            certificate_mode=args.certificate_mode,
            target=args.target,
            package=args.package,
            os_release=args.os_release,
        )

        if args.acknowledge_preview:
            acknowledge(result)

        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print(render_text(result))

            if args.interactive and result["status"] == "preview-ready":
                answer = input(
                    "\nAcknowledge this preview only? [y/N]: "
                ).strip().lower()

                if answer in ("y", "yes"):
                    acknowledge(result)
                    print(
                        "Preview acknowledged. "
                        "No installation was performed."
                    )
                else:
                    print("Preview not acknowledged.")

    except (ValueError, EOFError, KeyboardInterrupt) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
