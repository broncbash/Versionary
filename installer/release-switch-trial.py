#!/usr/bin/env python3
"""Isolated release switch and rollback exercise; never operates on /."""
import argparse
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_test_root(root):
    root = Path(root).absolute()
    if root == Path("/"):
        raise ValueError("Live filesystem root is forbidden")
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError("Unsafe isolated test root")
    return root


def active_identifier(app):
    link = app / "agent"
    if not link.is_symlink():
        raise ValueError("No active release symlink")
    target = os.readlink(link)
    prefix, suffix = "releases/", "/agent"
    identifier = target[len(prefix):-len(suffix)] if target.startswith(prefix) and target.endswith(suffix) else ""
    atomic = load("atomic-release.py", "patch_release_id_check")
    atomic.validate_release_identifier(identifier)
    return identifier


def switch_and_restore(*, root, package):
    root = require_test_root(root)
    app = root / "opt/arby-patch-agent"
    atomic = load("atomic-release.py", "patch_release_switch")
    validator = load("validate-package.py", "patch_release_validator")
    modules = validator.load_modules(Path(package))
    # Existing root must already have a valid active release. The switch is
    # confined to this isolated root; service state and config are untouched.
    previous = active_identifier(app)
    atomic.require_safe_path(app)
    atomic.require_safe_path(app / "releases")
    with atomic.install_lock(app):
        # Verify the original release before allowing any switch.
        atomic.activate_release(app, previous)
        candidate = atomic.stage_release(app, modules)
        try:
            atomic.activate_release(app, candidate)
            if active_identifier(app) != candidate:
                raise RuntimeError("Candidate activation mismatch")
        finally:
            atomic.activate_release(app, previous)
        if active_identifier(app) != previous:
            raise RuntimeError("Release restoration mismatch")
    return {
        "status": "restored",
        "mode": "isolated-release-switch",
        "previous_release": previous,
        "candidate_release": candidate,
        "active_release": previous,
        "production_installed": False,
        "systemd_started": False,
        "agent_enrolled": False,
        "configuration_changed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--package", required=True)
    args = parser.parse_args(argv)
    try:
        result = switch_and_restore(root=args.root, package=args.package)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Isolated release exercise failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
