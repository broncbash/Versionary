#!/usr/bin/env python3
"""Isolated, restartable transaction/recovery fault-injection harness.

No arbitrary root input is exposed by the public CLI. Parent creates and owns
a disposable root; child processes operate only on that root. NOT an installer.
"""
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

PARTS = ("release", "config", "ca", "service", "timer")
STATES = ("prepared",) + PARTS + ("verified", "recovering", "recovered")
EXIT_INTERRUPTED = 77


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 65536:
            raise ValueError("Unsafe or oversized trial file: " + str(path))
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read(65537)
    finally:
        os.close(fd)


def expected_prior():
    return {name: digest(("old:" + name).encode()) for name in PARTS}


def journal(root, state):
    if state not in STATES:
        raise ValueError("Unknown journal state")
    data = json.dumps({"version": 1, "state": state, "prior": expected_prior()},
                      sort_keys=True).encode()
    pending = root / "journal.pending"
    # Recovery after a crash between write and rename may leave a stale temp.
    if pending.is_symlink():
        raise ValueError("Symlinked pending journal")
    if pending.exists():
        pending.unlink()
    write(pending, data)
    os.replace(pending, root / "journal.json")
    sync_dir(root)


def read_journal(root):
    saved = json.loads(read_regular(root / "journal.json"))
    if (not isinstance(saved, dict) or set(saved) != {"version", "state", "prior"}
            or type(saved["version"]) is not int or saved["version"] != 1
            or saved["state"] not in STATES or saved["prior"] != expected_prior()):
        raise ValueError("Untrusted or malformed journal")
    return saved["state"]


def validate_root(root):
    if root.is_symlink() or not root.is_dir() or (root.stat().st_mode & 0o077):
        raise ValueError("Unsafe disposable root")
    for dirname in ("active", "prior"):
        directory = root / dirname
        if directory.is_symlink() or not directory.is_dir() or (directory.stat().st_mode & 0o077):
            raise ValueError("Unsafe disposable directory")
    for name in PARTS:
        if digest(read_regular(root / "prior" / name)) != expected_prior()[name]:
            raise ValueError("Prior generation corrupted")


def worker(root, operation, stop_at=None):
    if operation not in ("switch", "recover"):
        raise ValueError("Invalid worker operation")
    validate_root(root)
    if operation == "switch":
        if stop_at is not None and stop_at not in PARTS:
            raise ValueError("Unknown switch checkpoint")
        journal(root, "prepared")
        for name in PARTS:
            pending = root / "active" / (name + ".pending")
            write(pending, ("new:" + name).encode())
            os.replace(pending, root / "active" / name)
            sync_dir(root / "active")
            journal(root, name)
            if name == stop_at:
                os._exit(EXIT_INTERRUPTED)
        journal(root, "verified")
        return
    if stop_at is not None and stop_at not in PARTS:
        raise ValueError("Unknown recovery checkpoint")
    state = read_journal(root)
    if state == "recovered":
        for name in PARTS:
            if read_regular(root / "active" / name) != ("old:" + name).encode():
                raise ValueError("Recovered journal contradicts active assets")
        return
    # Preflight ALL backups and active assets before any replacement. An active
    # asset must be from either known generation, never arbitrary content.
    for name in PARTS:
        data = read_regular(root / "active" / name)
        if data not in (("old:" + name).encode(), ("new:" + name).encode()):
            raise ValueError("Unexpected active generation: " + name)
    journal(root, "recovering")
    for name in PARTS:
        pending = root / "active" / (name + ".restore")
        if pending.is_symlink():
            raise ValueError("Symlinked restore staging path")
        if pending.exists():
            pending.unlink()
        write(pending, read_regular(root / "prior" / name))
        os.replace(pending, root / "active" / name)
        sync_dir(root / "active")
        if name == stop_at:
            os._exit(EXIT_INTERRUPTED)
    journal(root, "recovered")


def run(stop_at="ca", tamper=None, recover_stop_at=None):
    if stop_at not in PARTS or (recover_stop_at is not None and recover_stop_at not in PARTS):
        raise ValueError("Unknown stop checkpoint")
    if tamper not in (None, "journal", "backup", "active", "journal_symlink",
                      "backup_symlink", "active_symlink", "restore_symlink"):
        raise ValueError("Unknown tamper mode")
    with tempfile.TemporaryDirectory(prefix="patch-command-restart-trial-") as temp:
        root = Path(temp)
        root.chmod(0o700)
        for name in ("active", "prior"):
            (root / name).mkdir(mode=0o700)
        for name in PARTS:
            data = ("old:" + name).encode()
            write(root / "active" / name, data)
            write(root / "prior" / name, data)
        command = [sys.executable, str(Path(__file__).resolve()), "_worker", str(root)]
        switched = subprocess.run(command + ["switch", stop_at], capture_output=True, text=True)
        if switched.returncode != EXIT_INTERRUPTED:
            raise RuntimeError("Expected independent switch worker termination: " + switched.stderr)
        if tamper == "journal":
            (root / "journal.json").write_text('{"version":0}')
        elif tamper == "backup":
            (root / "prior" / "ca").write_text("tampered")
        elif tamper == "active":
            (root / "active" / "ca").write_text("tampered")
        elif tamper in ("journal_symlink", "backup_symlink", "active_symlink"):
            path = {"journal_symlink": root / "journal.json",
                    "backup_symlink": root / "prior" / "ca",
                    "active_symlink": root / "active" / "ca"}[tamper]
            path.unlink()
            path.symlink_to(root / "prior" / "release")
        elif tamper == "restore_symlink":
            (root / "active" / "release.restore").symlink_to(root / "prior" / "release")
        recover_cmd = command + ["recover"]
        if recover_stop_at is not None:
            recover_cmd.append(recover_stop_at)
        recovered = subprocess.run(recover_cmd, capture_output=True, text=True)
        if tamper:
            if recovered.returncode == 0:
                raise RuntimeError("Tampered recovery was accepted")
            # The recovery refusal must not mark a transaction as recovered.
            if tamper not in ("journal", "journal_symlink") and read_journal(root) == "recovered":
                raise RuntimeError("Refused recovery was falsely finalized")
            return {"status": "refused", "tamper": tamper, "checkpoint": stop_at,
                    "production_installed": False, "systemd_started": False}
        if recover_stop_at:
            if recovered.returncode != EXIT_INTERRUPTED:
                raise RuntimeError("Expected interrupted recovery: " + recovered.stderr)
            recovered = subprocess.run(command + ["recover"], capture_output=True, text=True)
        if recovered.returncode != 0:
            raise RuntimeError("Recovery worker failed: " + recovered.stderr)
        # A third independent process must be able to verify idempotent recovery.
        repeated = subprocess.run(command + ["recover"], capture_output=True, text=True)
        if repeated.returncode != 0:
            raise RuntimeError("Idempotent recovery failed: " + repeated.stderr)
        if any(read_regular(root / "active" / name) != ("old:" + name).encode()
               for name in PARTS):
            raise RuntimeError("Restored generation mismatch")
        if read_journal(root) != "recovered":
            raise RuntimeError("Recovery journal not finalized")
        return {"status": "recovered", "mode": "disposable-independent-process-recovery",
                "checkpoint": stop_at, "recovery_interrupted_at": recover_stop_at,
                "idempotent_recovery_verified": True, "production_installed": False,
                "systemd_started": False, "agent_enrolled": False,
                "external_network_requests_made": False}


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "_worker":
        if len(sys.argv) not in (4, 5):
            raise SystemExit(2)
        worker(Path(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else None)
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--stop-at", choices=PARTS, default="ca")
        parser.add_argument("--tamper", choices=("journal", "backup", "active", "journal_symlink",
                                                "backup_symlink", "active_symlink", "restore_symlink"))
        parser.add_argument("--recover-stop-at", choices=PARTS)
        args = parser.parse_args()
        print(json.dumps(run(args.stop_at, args.tamper, args.recover_stop_at), indent=2))


if __name__ == "__main__":
    main()
