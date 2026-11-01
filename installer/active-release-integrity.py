#!/usr/bin/env python3
"""Read-only Versionary active-release content integrity verification.

Integrity is not authenticity, provenance, or rollback authorization.
"""

import argparse
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_integrity(root):
    inspector = load(
        "active-release-inspection.py",
        "versionary_integrity_inspector",
    )
    atomic = load(
        "atomic-release.py",
        "versionary_integrity_atomic",
    )

    result = inspector.inspect(root)

    response = {
        "product": "Versionary",
        "mode": "isolated-active-release-integrity",
        "active_release": result["active_release"],
        "active_present": result["active_present"],
        "integrity_verified": False,
        "authenticity_verified": False,
        "provenance_verified": False,
        "rollback_authorized": False,
        "changes_made": False,
        "production_approved": False,
    }

    if not result["active_present"]:
        response["status"] = "absent"
        return response

    root = Path(root).absolute()
    identifier = result["active_release"]
    release = (
        root / "opt/versionary-agent/releases" / identifier / "agent"
    )

    modules = {}

    for entry in release.iterdir():
        if entry.name == "__pycache__":
            atomic.require_safe_bytecode_cache(entry)
            continue

        atomic.require_safe_path(entry, directory=False)

        if not entry.name.endswith(".py"):
            raise ValueError("Unexpected release entry")

        modules[entry.name] = entry.read_bytes()

    if not modules:
        raise ValueError("Empty release")

    if atomic.release_id(modules) != identifier:
        raise ValueError("Active release integrity mismatch")

    response["integrity_verified"] = True
    response["status"] = "verified"
    response["module_count"] = len(modules)

    return response


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)

    try:
        result = verify_integrity(args.root)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Release integrity verification refused: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
