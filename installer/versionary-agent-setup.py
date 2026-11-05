#!/usr/bin/env python3
"""Versionary portable, unprivileged agent setup.

Configures a private agent state directory using the existing CLI.
Does not install services, register agents, or contact a server.
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.config import validate_server
from versionary_agent_cli import DEFAULT_STATE, setup, state_paths


def validate_ca(path):
    if not path:
        raise ValueError("A CA certificate path is required")

    ca = Path(path).expanduser().absolute()

    if ca.is_symlink() or not ca.is_file():
        raise ValueError(
            "CA certificate must be an existing regular file, not a symlink"
        )

    return ca


def prepare(server, ca_cert, state_dir):
    server = validate_server(server)
    ca = validate_ca(ca_cert)

    paths = state_paths(state_dir)

    if paths["config"].exists() or paths["config"].is_symlink():
        raise FileExistsError(
            "Agent configuration already exists; refusing overwrite"
        )

    return server, ca, paths


def run(argv=None):
    parser = argparse.ArgumentParser(
        description="Versionary portable agent setup"
    )

    parser.add_argument("--server")
    parser.add_argument("--ca-cert")
    parser.add_argument(
        "--state-dir",
        default=str(DEFAULT_STATE),
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for missing connection settings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview without writing files",
    )

    args = parser.parse_args(argv)

    try:
        server = args.server
        ca_cert = args.ca_cert

        if args.interactive:
            if not sys.stdin.isatty():
                raise ValueError(
                    "Interactive mode requires a terminal"
                )

            if not server:
                server = input(
                    "Versionary HTTPS server URL: "
                ).strip()

            if not ca_cert:
                ca_cert = input(
                    "Trusted CA certificate path: "
                ).strip()

        if not server or not ca_cert:
            raise ValueError(
                "Provide --server and --ca-cert, "
                "or use --interactive"
            )

        server, ca, paths = prepare(
            server, ca_cert, args.state_dir
        )

        print("Versionary agent setup")
        print("Server:", server)
        print("CA certificate:", ca)
        print("State directory:", paths["root"])

        if args.dry_run:
            print("[DRY RUN] No files created")
            return 0

        setup(paths, server, str(ca))

        print("[OK] Private configuration created")
        print("[OK] No service installed")
        print("[OK] No agent registered")
        print("[OK] No network connection attempted")
        print()
        print("Next steps:")
        print("  1. Register the agent manually")
        print("  2. Approve it in Versionary")
        print("  3. Complete enrollment")
        print()
        print("Use versionary_agent_cli.py for those operations.")

        return 0

    except (RuntimeError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
