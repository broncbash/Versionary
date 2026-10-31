#!/usr/bin/env python3
"""Development-only Versionary trust-state administration CLI.

Not a production installer. This tool does not manage services,
agents, production enrollment, or operating-system trust stores.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "versionary_trust_admin_state",
    ROOT / "installer/release-trust-state.py",
)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


def summary(record):
    """Return metadata only; never expose stored authority/policy bytes."""
    return {
        "authority_key_id": record["authority_key_id"],
        "policy_version": record["policy_version"],
        "policy_sha256": record["policy_sha256"],
        "bootstrapped": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--database", required=True, type=Path)
    bootstrap.add_argument("--authority-public", required=True, type=Path)

    inspect = sub.add_parser("inspect")
    inspect.add_argument("--database", required=True, type=Path)

    install = sub.add_parser("install")
    install.add_argument("--database", required=True, type=Path)
    install.add_argument("--policy", required=True, type=Path)
    install.add_argument("--signature", required=True, type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "bootstrap":
            identity = state.initialize(
                args.database, args.authority_public
            )
            result = {
                "status": "bootstrapped",
                "authority_key_id": identity,
                "policy_version": 0,
            }

        elif args.command == "inspect":
            result = summary(state.read_state(args.database))
            result["status"] = "ok"

        elif args.command == "install":
            version = state.install_update(
                args.database, args.policy, args.signature
            )
            result = summary(state.read_state(args.database))
            result["status"] = "installed"
            result["installed_version"] = version

        else:
            parser.error("Unknown command")

        print(json.dumps(result, sort_keys=True))
        return 0

    except (
        state.TrustStateError,
        state._UPDATES.PolicyUpdateError,
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
