#!/usr/bin/env python3
"""Restore verified public installation assets into an empty disposable root.

This is intentionally NOT a production restore or in-place rollback.
"""
import argparse
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def restore(snapshot_dir, root):
    snapshot = load("patch_restore_snapshot", "installation-snapshot.py")
    inventory = load("patch_restore_inventory", "installation-inventory.py")
    snapshot_dir = Path(snapshot_dir).absolute()
    root = Path(root).absolute()
    if root == Path("/") or root == snapshot_dir or root.is_relative_to(snapshot_dir) or snapshot_dir.is_relative_to(root):
        raise ValueError("Live root or overlapping snapshot and destination forbidden")
    snapshot.verify(snapshot_dir)
    # An empty root is the only supported destination. No replacements, ever.
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Destination must be an owner-controlled private directory (0700)")
    if any(root.iterdir()):
        raise ValueError("Destination must be empty; existing installations cannot be replaced")
    manifest = json.loads((snapshot_dir / "manifest.json").read_bytes())
    records = manifest["assets"]
    # Recheck snapshot before any writes; snapshot must be owner-controlled.
    for index, relative in enumerate(inventory.FILES):
        record = records[relative]
        if record["present"]:
            mode = int(record["mode"], 8)
            if mode & 0o022 or mode & ~0o777 or mode == 0:
                raise ValueError("Unsafe asset mode")
    written = 0
    try:
        for index, relative in enumerate(inventory.FILES):
            record = records[relative]
            if not record["present"]:
                continue
            path = root
            for component in Path(relative).parts[:-1]:
                path = path / component
                try:
                    path.mkdir(mode=0o700)
                except FileExistsError:
                    info = path.lstat()
                    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                        raise ValueError("Unsafe destination directory")
            destination = path / Path(relative).name
            source = snapshot_dir / f"asset-{index}"
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_uid != os.geteuid():
                    raise ValueError("Snapshot asset changed")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    data = stream.read(1048577)
            finally:
                os.close(fd)
            import hashlib
            if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                raise ValueError("Snapshot asset changed")
            out = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            try:
                os.fchmod(out, int(record["mode"], 8))
                with os.fdopen(out, "wb", closefd=False) as stream:
                    stream.write(data)
                    stream.flush()
                os.fsync(out)
            finally:
                os.close(out)
            written += 1
        observed = inventory.inspect(root)["assets"]
        if observed != records:
            raise ValueError("Restored asset inventory differs from snapshot")
    except BaseException:
        # Preserve partial destination for forensic inspection; never auto-delete.
        raise
    return {"product": "Patch Command", "status": "restored", "mode": "isolated-empty-root-only",
            "asset_count": written, "private_state_restored": False,
            "production_installed": False, "systemd_started": False, "agent_enrolled": False}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    try:
        result = restore(args.snapshot, args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Restore refused or failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
