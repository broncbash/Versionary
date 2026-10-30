#!/usr/bin/env python3
"""Read-only comparison of a disposable installation and verified asset snapshot.

Never applies changes, starts services, or accesses production root.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plan(root, snapshot_dir):
    inventory = _load("installation-inventory.py", "patch_plan_inventory")
    snapshots = _load("installation-snapshot.py", "patch_plan_snapshots")
    root = Path(root).absolute()
    snapshot_dir = Path(snapshot_dir).absolute()
    if (root == Path("/") or root == snapshot_dir
            or root.is_relative_to(snapshot_dir) or snapshot_dir.is_relative_to(root)):
        raise ValueError("Production or overlapping paths forbidden")
    snapshots.verify(snapshot_dir)
    current = inventory.inspect(root)
    # Manifest was verified; still explicitly reject any changed metadata.
    manifest = json.loads((snapshot_dir / "manifest.json").read_bytes())
    if (manifest.get("version") != 1 or set(manifest.get("assets", {})) != set(inventory.FILES)):
        raise ValueError("Snapshot metadata changed")
    changes = []
    for relative in inventory.FILES:
        old = current["assets"][relative]
        target = manifest["assets"][relative]
        if old == target:
            action = "unchanged"
        elif not old["present"] and target["present"]:
            action = "create"
        elif old["present"] and not target["present"]:
            action = "remove"
        else:
            action = "replace"
        changes.append({"path": relative, "action": action,
                        "current": old, "proposed": target})
    blockers = [
        "No production installer or coordinated apply transaction is authorized",
        "Snapshot is not authenticated against an independent trust anchor",
        "Code-release and systemd service lifecycle are not coordinated",
    ]
    if current["private_state"] == "present-not-inspected":
        blockers.append("Private state exists and is intentionally excluded from rollback")
    if any(item["action"] == "remove" for item in changes):
        blockers.append("Proposed asset removal requires explicit review")
    return {
        "product": "Patch Command", "status": "planned", "mode": "read-only-isolated-rollback-plan",
        "changes": changes, "change_count": sum(item["action"] != "unchanged" for item in changes),
        "blockers": blockers, "apply_allowed": False, "changes_made": False,
        "credential_contents_read": False, "production_installed": False,
        "systemd_started": False, "agent_enrolled": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Existing disposable installation root")
    parser.add_argument("--snapshot", required=True, help="Verified private asset snapshot")
    args = parser.parse_args(argv)
    try:
        result = plan(args.root, args.snapshot)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Rollback plan refused: {exc}\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
