#!/usr/bin/env python3
"""Inspect or explicitly recover interrupted isolated code-release trials.

Default mode is read-only. Never targets the live filesystem or starts services.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(*, root, recover=False):
    journal = load("release-recovery.py", "patch_command_recovery_journal")
    atomic = load("atomic-release.py", "patch_command_recovery_atomic")
    root = Path(root).absolute()
    app = journal.safe_app(root)
    # Even read-only inspection takes the installer lock to avoid racing a trial.
    with atomic.install_lock(app):
        record = journal.read(root)
        previous = record["previous"]
        candidate = record["candidate"]
        active = app / "agent"
        current = os.readlink(active) if active.is_symlink() else None
        if not recover:
            return {
                "status": "recovery-pending",
                "mode": "read-only",
                "previous_release": previous,
                "candidate_release": candidate,
                "active_link": current,
                "changes_made": False,
                "production_installed": False,
                "systemd_started": False,
                "agent_enrolled": False,
            }
        # Fail closed if another unexpected release is active.
        allowed = {f"releases/{previous}/agent", f"releases/{candidate}/agent"}
        if current not in allowed:
            raise RuntimeError("Unexpected active release; manual investigation required")
        restored = journal.recover(root, atomic)
        if os.readlink(active) != f"releases/{restored}/agent":
            raise RuntimeError("Restored release link mismatch")
        return {
            "status": "restored",
            "mode": "explicit-isolated-recovery",
            "active_release": restored,
            "recovery_marker_cleared": True,
            "production_installed": False,
            "systemd_started": False,
            "agent_enrolled": False,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Pre-existing isolated test root; / is forbidden")
    parser.add_argument("--recover", action="store_true", help="Explicitly restore prior code release")
    args = parser.parse_args(argv)
    try:
        result = inspect(root=args.root, recover=args.recover)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Recovery inspection failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
