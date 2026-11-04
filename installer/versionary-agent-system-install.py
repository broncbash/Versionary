#!/usr/bin/env python3
"""Controlled Versionary agent system-installation coordinator.

Beta authorization validation only. Installation is not implemented.
"""

import argparse
import importlib.util
import os
import platform
import sys
from pathlib import Path


AUTHORIZATION = "I_AUTHORIZE_VERSIONARY_BETA_SYSTEM_INSTALL"


class InstallationNotImplemented(RuntimeError):
    pass


def validate_authorization(authorization, root, effective_uid=None):
    if authorization != AUTHORIZATION:
        raise ValueError("Explicit beta authorization required")

    if platform.system() != "Linux":
        raise ValueError("Linux is required")

    if effective_uid is None:
        effective_uid = os.geteuid()

    if effective_uid != 0:
        raise PermissionError("Root privileges required")

    root = Path(root)

    if not root.is_absolute() or str(root) != "/":
        raise ValueError("System installation requires exact root /")

    return root


def load_preflight():
    path = (
        Path(__file__).resolve().parent
        / "versionary-agent-system-preflight.py"
    )
    spec = importlib.util.spec_from_file_location(
        "versionary_system_install_preflight",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_conflicts():
    path = (
        Path(__file__).resolve().parent
        / "versionary-agent-system-conflicts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "versionary_system_install_conflicts",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_content():
    path = (
        Path(__file__).resolve().parent
        / "versionary-agent-system-content.py"
    )
    spec = importlib.util.spec_from_file_location(
        "versionary_system_install_content",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install(
    authorization,
    root,
    distribution=None,
    server=None,
    ca_cert=None,
):
    validate_authorization(authorization, root)

    if distribution is None or server is None or ca_cert is None:
        raise ValueError(
            "Distribution, HTTPS server and CA certificate required"
        )

    preflight = load_preflight()
    preflight.preflight(distribution, server, ca_cert)

    conflicts = load_conflicts()
    conflicts.inspect(Path(root))

    content = load_content()
    payloads = content.expected_payloads(
        distribution,
        server,
        ca_cert,
    )
    content.inspect_existing(Path(root), payloads)

    raise InstallationNotImplemented(
        "Real-system installation is not yet implemented"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authorize-beta",
        required=True,
        help="Exact authorization phrase required",
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Must be exactly /",
    )
    parser.add_argument("--distribution", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--ca-cert", required=True)
    args = parser.parse_args()

    try:
        install(
            args.authorize_beta,
            args.root,
            args.distribution,
            args.server,
            args.ca_cert,
        )
    except (
        ValueError,
        PermissionError,
        InstallationNotImplemented,
    ) as exc:
        print("[STOP]", exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
