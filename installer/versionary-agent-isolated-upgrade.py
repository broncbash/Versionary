#!/usr/bin/env python3
"""Conservative isolated-root Versionary upgrade prototype.

Not authorized for real-system installation.

A persistent transaction directory records previous and proposed
payloads. Interrupted operations require explicit recovery.

This prototype does NOT guarantee crash consistency, atomic
multi-file upgrades, or safety against concurrent filesystem
mutation by a privileged adversary.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import uuid

HERE = Path(__file__).resolve().parent
TX_NAME = ".versionary-upgrade-transaction"
MANIFEST_NAME = "manifest.json"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    "versionary-agent-isolated-coordinator.py",
    "versionary_upgrade_coordinator",
)

conflicts = load(
    "versionary-agent-system-conflicts.py",
    "versionary_upgrade_conflicts",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_root(root):
    root = coordinator.validate_root(root)
    conflicts.inspect(root)
    return root


def validate_payloads(payloads):
    if not isinstance(payloads, dict):
        raise ValueError("Payload mapping required")

    if set(payloads) != set(coordinator.MODES):
        raise ValueError("Unexpected upgrade inventory")

    for name, data in payloads.items():
        if not isinstance(data, bytes) or not data:
            raise ValueError(f"Invalid payload: {name}")


def safe_target(root, name):
    target = root / name

    # All parents must already exist and must be actual directories.
    parent = root
    for component in Path(name).parts[:-1]:
        parent = parent / component
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Unsafe parent: {name}")
        if info.st_uid != os.geteuid():
            raise ValueError(f"Unsafe parent owner: {name}")
        if info.st_mode & 0o022:
            raise ValueError(f"Writable parent: {name}")

    info = target.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"Unsafe target: {name}")
    if info.st_uid != os.geteuid():
        raise ValueError(f"Unsafe target owner: {name}")
    if info.st_nlink != 1:
        raise ValueError(f"Hardlinked target: {name}")
    if info.st_mode & 0o022:
        raise ValueError(f"Writable target: {name}")

    return target


def read_existing(root, expected):
    result = {}
    for name, content in expected.items():
        target = safe_target(root, name)
        actual = target.read_bytes()
        if actual != content:
            raise ValueError(
                f"Existing payload differs from expected: {name}"
            )
        result[name] = actual
    return result


def write_exclusive(path, data, mode=0o600):
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def transaction_path(root):
    return root / TX_NAME


def inspect_pending(root):
    root = coordinator.validate_root(root)
    tx = transaction_path(root)

    try:
        info = tx.lstat()
    except FileNotFoundError:
        return {"status": "clear"}

    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise ValueError("Unsafe upgrade transaction directory")

    return {"status": "recovery_required"}


def prepare(root, old, new):
    root = validate_root(root)
    validate_payloads(old)
    validate_payloads(new)

    if inspect_pending(root)["status"] != "clear":
        raise RuntimeError("Pending upgrade requires review")

    recovery = load(
        "versionary-agent-system-recovery.py",
        "versionary_upgrade_install_recovery",
    )

    if recovery.inspect_pending(root)["status"] != "clear":
        raise RuntimeError(
            "Pending installation recovery requires review"
        )

    read_existing(root, old)

    if old == new:
        return None

    tx = transaction_path(root)
    tx.mkdir(mode=0o700)

    try:
        manifest = {"version": 1, "files": {}}

        for index, name in enumerate(sorted(old)):
            before = old[name]
            after = new[name]

            write_exclusive(
                tx / f"old-{index:03d}",
                before,
            )
            write_exclusive(
                tx / f"new-{index:03d}",
                after,
            )

            manifest["files"][name] = {
                "old": f"old-{index:03d}",
                "new": f"new-{index:03d}",
                "old_sha256": sha(before),
                "new_sha256": sha(after),
                "mode": coordinator.MODES[name],
            }

        write_exclusive(
            tx / MANIFEST_NAME,
            (json.dumps(manifest, sort_keys=True) + "\n").encode(),
        )

        # This sync improves durability of the staging directory,
        # but does not establish end-to-end crash consistency.
        fd = os.open(tx, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

        # Persist the transaction directory entry in its parent
        # before allowing any installed payload to be replaced.
        # If this fails, retain the journal and abort the upgrade.
        fd = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

        return tx

    except BaseException:
        # A partially prepared transaction is deliberately retained.
        # Never erase evidence of an uncertain operation.
        raise


def read_manifest(root):
    root = validate_root(root)
    tx = transaction_path(root)

    if inspect_pending(root)["status"] != "recovery_required":
        raise RuntimeError("No pending upgrade")

    manifest_path = tx / MANIFEST_NAME
    info = manifest_path.lstat()

    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_nlink != 1
        or info.st_mode & 0o077
        or info.st_size > 1024 * 1024
    ):
        raise ValueError("Unsafe upgrade manifest")

    try:
        manifest = json.loads(manifest_path.read_bytes())
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid upgrade manifest JSON") from exc

    if not isinstance(manifest, dict):
        raise ValueError("Upgrade manifest must be an object")

    if (
        manifest.get("version") != 1
        or not isinstance(manifest.get("files"), dict)
        or set(manifest["files"]) != set(coordinator.MODES)
    ):
        raise ValueError("Invalid upgrade manifest")

    # The manifest must reference exactly the snapshot names
    # produced by prepare(). Never accept aliases, traversal,
    # duplicate references, or reordered snapshot identities.
    expected_snapshots = set()

    for index, name in enumerate(sorted(coordinator.MODES)):
        entry = manifest["files"][name]

        if not isinstance(entry, dict):
            raise ValueError("Invalid manifest entry")

        for kind in ("old", "new"):
            filename = f"{kind}-{index:03d}"

            if entry.get(kind) != filename:
                raise ValueError(
                    "Unexpected snapshot filename"
                )

            if filename in expected_snapshots:
                raise ValueError(
                    "Duplicate snapshot reference"
                )

            expected_snapshots.add(filename)

    for name, entry in manifest["files"].items():
        for kind in ("old", "new"):
            filename = entry.get(kind)
            expected = entry.get(kind + "_sha256")

            if not isinstance(filename, str):
                raise ValueError("Invalid snapshot name")
            if not isinstance(expected, str):
                raise ValueError("Invalid snapshot digest")
            if len(expected) != 64:
                raise ValueError("Invalid snapshot digest")
            if filename.startswith("/") or "/" in filename:
                raise ValueError("Unsafe snapshot name")

            path = tx / filename
            info = path.lstat()

            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_nlink != 1
                or info.st_mode & 0o077
                or info.st_size > 16 * 1024 * 1024
            ):
                raise ValueError("Unsafe snapshot")

            if sha(path.read_bytes()) != expected:
                raise ValueError("Snapshot checksum mismatch")

        if entry.get("mode") != coordinator.MODES[name]:
            raise ValueError("Snapshot mode mismatch")

    return manifest


def classify(root, manifest):
    root = validate_root(root)
    tx = transaction_path(root)
    result = {}

    for name, entry in manifest["files"].items():
        target = safe_target(root, name)
        current = target.read_bytes()

        old = (tx / entry["old"]).read_bytes()
        new = (tx / entry["new"]).read_bytes()

        if current == old:
            result[name] = "old"
        elif current == new:
            result[name] = "new"
        else:
            raise ValueError(
                f"Unexpected file contents during recovery: {name}"
            )

    return result


def replace_file(target, content, mode):
    staging = target.parent / (
        ".versionary-stage-" + uuid.uuid4().hex
    )

    try:
        write_exclusive(staging, content, mode)
        os.replace(staging, target)

        fd = os.open(
            target.parent,
            os.O_RDONLY | os.O_DIRECTORY,
        )
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    finally:
        staging.unlink(missing_ok=True)


def apply(root, old, new, fail_after=None):
    root = validate_root(root)
    tx = prepare(root, old, new)

    if tx is None:
        return {"status": "unchanged", "updated": 0}

    manifest = read_manifest(root)

    changed = 0

    for name, entry in sorted(manifest["files"].items()):
        if old[name] == new[name]:
            continue

        if fail_after is not None and changed >= fail_after:
            raise RuntimeError("Simulated interrupted upgrade")

        # Refuse to overwrite files that changed since preparation.
        target = safe_target(root, name)
        if target.read_bytes() != old[name]:
            raise RuntimeError(
                f"Concurrent modification detected: {name}"
            )

        replace_file(
            target,
            new[name],
            entry["mode"],
        )
        changed += 1

    return {
        "status": "applied_recovery_review_required",
        "updated": changed,
    }


def recover_to_old(root):
    """Explicitly restore the original payload set.

    Does not remove the transaction journal. A separate review
    is required before clearing the completed transaction.
    """
    root = validate_root(root)
    manifest = read_manifest(root)
    states = classify(root, manifest)
    tx = transaction_path(root)

    restored = 0

    for name, entry in sorted(manifest["files"].items()):
        if states[name] == "old":
            continue

        target = safe_target(root, name)
        new = (tx / entry["new"]).read_bytes()

        if target.read_bytes() != new:
            raise RuntimeError(
                f"Concurrent recovery conflict: {name}"
            )

        replace_file(
            target,
            (tx / entry["old"]).read_bytes(),
            entry["mode"],
        )
        restored += 1

    return {
        "status": "restored_review_required",
        "restored": restored,
    }


def review_complete(root):
    """Read-only determination of whether original files are restored."""
    manifest = read_manifest(root)
    states = classify(root, manifest)

    return {
        "status": (
            "original_restored"
            if all(state == "old" for state in states.values())
            else "recovery_required"
        ),
        "files": states,
    }


def finalization_assessment(root):
    """Read-only assessment; never remove or authorize journal cleanup.

    This is an advisory result, not an authorization to delete
    transaction evidence or resume installation.
    """
    root = validate_root(root)

    if inspect_pending(root)["status"] == "clear":
        return {
            "status": "no_transaction",
            "eligible_for_review": False,
            "cleanup_authorized": False,
        }

    # Check journal inventory before trusting the manifest or
    # reading snapshot contents. Unexpected entries are evidence
    # requiring investigation, never automatic cleanup.
    tx = transaction_path(root)
    expected = {MANIFEST_NAME}

    for index, _name in enumerate(
        sorted(coordinator.MODES)
    ):
        expected.add(f"old-{index:03d}")
        expected.add(f"new-{index:03d}")

    actual = {entry.name for entry in tx.iterdir()}
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)

    if unexpected or missing:
        return {
            "status": "recovery_or_investigation_required",
            "eligible_for_review": False,
            "cleanup_authorized": False,
            "unexpected_entries": unexpected,
            "missing_entries": missing,
            "files": {},
        }

    manifest = read_manifest(root)
    states = classify(root, manifest)

    restored = all(
        state == "old" for state in states.values()
    )

    return {
        "status": (
            "review_candidate"
            if restored and not unexpected
            else "recovery_or_investigation_required"
        ),
        "eligible_for_review": restored and not unexpected,
        "cleanup_authorized": False,
        "unexpected_entries": unexpected,
        "files": states,
    }
