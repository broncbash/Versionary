#!/usr/bin/env python3
"""Create or verify a private snapshot of isolated installation assets.

Snapshots exclude enrollment credentials and private state. No live-root support.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def inventory_module():
    spec = importlib.util.spec_from_file_location("patch_snapshot_inventory", HERE / "installation-inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_directory(path):
    path = Path(path).absolute()
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077):
        raise ValueError("Snapshot directory must be private and owner-controlled")
    return path


def _read_asset(root, relative, expected):
    path = root
    for part in Path(relative).parts[:-1]:
        path = path / part
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError("Unsafe source directory")
    path = path / Path(relative).name
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > 1048576):
            raise ValueError("Unsafe source file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(1048577)
    finally:
        os.close(fd)
    if (len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]
            or oct(stat.S_IMODE(info.st_mode)) != expected["mode"]):
        raise ValueError("Source changed during snapshot")
    return data


def snapshot(root, destination):
    root = Path(root).absolute()
    source = inventory_module().inspect(root)
    destination = Path(destination).absolute()
    if destination == root or destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("Snapshot must be outside the installation tree")
    parent = safe_directory(destination.parent)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Snapshot destination already exists")
    # An exclusive private directory prevents replacing existing snapshots.
    destination.mkdir(mode=0o700)
    try:
        records = source["assets"]
        manifest = {"version": 1, "assets": records, "private_state": source["private_state"]}
        for index, (relative, item) in enumerate(records.items()):
            if not item["present"]:
                continue
            data = _read_asset(root, relative, item)
            path = destination / f"asset-{index}"
            with path.open("xb") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        manifest_path = destination / "manifest.json"
        with manifest_path.open("xb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(json.dumps(manifest, sort_keys=True).encode())
            output.flush()
            os.fsync(output.fileno())
        fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        # Do not delete a partial snapshot: leave it for inspection.
        raise
    return verify(destination)


def verify(destination):
    destination = safe_directory(destination)
    entries = list(destination.iterdir())
    for entry in entries:
        info = entry.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
                or info.st_size > 1048576):
            raise ValueError("Unsafe snapshot entry")
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    inventory = inventory_module()
    if (not isinstance(manifest, dict) or manifest.get("version") != 1
            or not isinstance(manifest.get("assets"), dict)
            or set(manifest["assets"]) != set(inventory.FILES)):
        raise ValueError("Invalid snapshot manifest")
    expected_entries = {"manifest.json"}
    for index, relative in enumerate(inventory.FILES):
        item = manifest["assets"][relative]
        if not isinstance(item, dict) or not isinstance(item.get("present"), bool):
            raise ValueError("Invalid snapshot asset record")
        if not item["present"]:
            if set(item) != {"present"}:
                raise ValueError("Invalid absent asset record")
            continue
        if (set(item) != {"present", "sha256", "size", "mode"}
                or not isinstance(item["size"], int) or isinstance(item["size"], bool)
                or not 0 <= item["size"] <= 1048576
                or not isinstance(item["sha256"], str) or len(item["sha256"]) != 64
                or not isinstance(item["mode"], str)):
            raise ValueError("Invalid asset metadata")
        name = f"asset-{index}"
        expected_entries.add(name)
        data = (destination / name).read_bytes()
        if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Snapshot integrity mismatch")
    if {p.name for p in entries} != expected_entries:
        raise ValueError("Unexpected snapshot entries")
    return {"product": "Patch Command", "status": "verified",
            "mode": "isolated-asset-snapshot", "asset_count": len(expected_entries) - 1,
            "private_state_copied": False, "production_installed": False,
            "systemd_started": False, "agent_enrolled": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Pre-existing isolated installation root")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.verify_only and not args.root:
            parser.error("--root required when creating a snapshot")
        result = verify(args.destination) if args.verify_only else snapshot(args.root, args.destination)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Snapshot failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
