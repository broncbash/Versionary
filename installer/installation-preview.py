#!/usr/bin/env python3
"""Read-only, portable installation configuration preview.

This module describes intended installation artifacts.
It never writes files, invokes installers, contacts servers,
or authorizes production deployment.
"""

import argparse
import json
import sys
from pathlib import Path


AGENT_ARTIFACTS = (
    {
        "path": "/opt/versionary-agent",
        "purpose": "Versioned agent application releases",
        "kind": "directory",
    },
    {
        "path": "/etc/versionary-agent",
        "purpose": "Agent configuration and trusted CA",
        "kind": "directory",
    },
    {
        "path": "/var/lib/versionary-agent",
        "purpose": "Private agent identity and persistent state",
        "kind": "directory",
        "permissions": "0700",
    },
    {
        "path": "/etc/versionary-agent/config.json",
        "purpose": "Validated agent configuration",
        "kind": "file",
    },
    {
        "path": "/etc/versionary-agent/ca.crt",
        "purpose": "Trusted server CA certificate",
        "kind": "file",
    },
    {
        "path": "/etc/systemd/system/versionary-agent.service",
        "purpose": "Agent service definition",
        "kind": "file",
        "activation": "disabled",
    },
    {
        "path": "/etc/systemd/system/versionary-agent.timer",
        "purpose": "Agent scheduling definition",
        "kind": "file",
        "activation": "disabled",
    },
)


class PreviewError(ValueError):
    """Invalid installation preview request."""


def create_preview(
    *,
    role,
    server=None,
    ca_cert=None,
    certificate_mode="existing-ca",
    target="disposable",
):
    if role not in ("agent", "server"):
        raise PreviewError("Unsupported installation role")

    if target != "disposable":
        raise PreviewError("Only disposable installation targets are supported")

    if certificate_mode not in ("existing-ca", "generate-test-ca"):
        raise PreviewError("Unsupported certificate mode")

    if role == "server":
        if server or ca_cert:
            raise PreviewError(
                "Server preview does not accept agent connection options"
            )

        return {
            "schema_version": 1,
            "role": "server",
            "status": "not-implemented",
            "target": target,
            "artifacts": [],
            "configuration": {},
            "certificate": {
                "mode": "not-configured",
                "private_key_in_manifest": False,
            },
            "operations": [],
            "safety": safety_policy(),
        }

    if not server:
        raise PreviewError("Agent server URL is required")

    # Import the canonical validator from the existing wizard.
    import importlib.util

    wizard_path = Path(__file__).resolve().parent / "setup-wizard.py"
    spec = importlib.util.spec_from_file_location(
        "patch_preview_wizard", wizard_path
    )
    wizard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wizard)

    server = wizard.validate_server(server)

    if certificate_mode == "existing-ca" and not ca_cert:
        raise PreviewError("Existing CA mode requires --ca-cert")

    if certificate_mode == "generate-test-ca" and ca_cert:
        raise PreviewError(
            "Test CA generation cannot be combined with --ca-cert"
        )

    certificate = {
        "mode": certificate_mode,
        "private_key_in_manifest": False,
        "network_trust_changed": False,
        "source": str(ca_cert) if ca_cert else None,
        "generation_permitted": False,
    }

    operations = [
        {
            "step": "preflight",
            "description": "Validate host, package, and certificate inputs",
            "enabled": False,
        },
        {
            "step": "stage",
            "description": "Stage files under a verified disposable root",
            "enabled": False,
        },
        {
            "step": "audit",
            "description": "Verify staged installation integrity",
            "enabled": False,
        },
        {
            "step": "review",
            "description": "Review evidence before further authorization",
            "enabled": False,
        },
    ]

    return {
        "schema_version": 1,
        "role": "agent",
        "status": "preview-only",
        "target": target,
        "artifacts": [dict(item) for item in AGENT_ARTIFACTS],
        "configuration": {
            "server": server,
            "ca_cert": "/etc/versionary-agent/ca.crt",
        },
        "certificate": certificate,
        "operations": operations,
        "safety": safety_policy(),
    }


def safety_policy():
    return {
        "production_installation_enabled": False,
        "live_host_mutations_enabled": False,
        "network_requests_enabled": False,
        "agent_enrollment_enabled": False,
        "service_activation_enabled": False,
        "changes_made": False,
        "approval_required": True,
    }


def render_text(preview):
    lines = [
        "PATCH COMMAND — INSTALLATION PREVIEW",
        "=" * 44,
        f"Role: {preview['role']}",
        f"Status: {preview['status']}",
        f"Target: {preview['target']}",
        f"Certificate mode: {preview['certificate']['mode']}",
        "",
        "PROPOSED ARTIFACTS",
    ]

    if preview["artifacts"]:
        for item in preview["artifacts"]:
            lines.append(f"  {item['path']}")
            lines.append(f"    {item['purpose']}")
    else:
        lines.append("  None — installer not implemented")

    lines.extend([
        "",
        "SECURITY",
        "  Production installation: DISABLED",
        "  Service activation: DISABLED",
        "  Agent enrollment: DISABLED",
        "  Network requests: DISABLED",
        "  Changes made: NONE",
        "",
        "This is a preview, not an installation.",
    ])

    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("agent", "server"), required=True)
    parser.add_argument("--server")
    parser.add_argument("--ca-cert")
    parser.add_argument(
        "--certificate-mode",
        choices=("existing-ca", "generate-test-ca"),
        default="existing-ca",
    )
    parser.add_argument("--target", default="disposable")
    parser.add_argument("--format", choices=("text", "json"), default="text")

    args = parser.parse_args(argv)

    try:
        preview = create_preview(
            role=args.role,
            server=args.server,
            ca_cert=args.ca_cert,
            certificate_mode=args.certificate_mode,
            target=args.target,
        )
    except PreviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(preview, indent=2))
    else:
        print(render_text(preview))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
