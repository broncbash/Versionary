#!/usr/bin/env python3
"""Self-contained filesystem transaction exercise, never an installer.

All working files live in a TemporaryDirectory created by this process.
No root/path argument is accepted. Recovery uses a persisted step journal.
"""
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

NAMES = ("release", "config", "ca", "service", "timer")
STAGES = ("prepared",) + NAMES + ("verified",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(data)
            out.flush()
            os.fsync(fd)
    finally:
        os.close(fd)


def journal_write(root, state, expected):
    path = root / "journal.json"
    temporary = root / "journal.pending"
    payload = json.dumps({"version": 1, "state": state, "expected": expected},
                         sort_keys=True).encode()
    write_new(temporary, payload)
    os.replace(temporary, path)
    sync_directory(root)


def run(fail_after=None):
    if fail_after is not None and fail_after not in STAGES:
        raise ValueError("Unknown failure checkpoint")
    with tempfile.TemporaryDirectory(prefix="patch-command-disposable-") as location:
        root = Path(location)
        live = root / "assets"
        old = root / "previous"
        new = root / "candidate"
        for directory in (live, old, new):
            directory.mkdir(mode=0o700)
        previous = {name: ("previous:" + name).encode() for name in NAMES}
        candidate = {name: ("candidate:" + name).encode() for name in NAMES}
        for name in NAMES:
            write_new(live / name, previous[name])
            write_new(old / name, previous[name])
            write_new(new / name, candidate[name])
        expected = {name: sha(previous[name]) for name in NAMES}
        journal_write(root, "prepared", expected)
        failed = fail_after == "prepared"
        reached = ["prepared"]
        if not failed:
            for name in NAMES:
                # Exclusive staging and atomic per-file replace. This is NOT
                # atomic across all assets.
                pending = live / (name + ".pending")
                write_new(pending, candidate[name])
                os.replace(pending, live / name)
                sync_directory(live)
                journal_write(root, name, expected)
                reached.append(name)
                if fail_after == name:
                    failed = True
                    break
        if not failed:
            if any((live / name).read_bytes() != candidate[name] for name in NAMES):
                raise RuntimeError("Candidate verification mismatch")
            journal_write(root, "verified", expected)
            reached.append("verified")
            failed = fail_after == "verified"
        if failed:
            persisted = json.loads((root / "journal.json").read_text())
            if persisted["state"] != reached[-1] or persisted["expected"] != expected:
                raise RuntimeError("Recovery journal mismatch")
            for name in reversed(NAMES):
                source = (old / name).read_bytes()
                if sha(source) != expected[name]:
                    raise RuntimeError("Backup digest mismatch")
                pending = live / (name + ".restore")
                write_new(pending, source)
                os.replace(pending, live / name)
                sync_directory(live)
            journal_write(root, "recovered", expected)
            reached.append("recovered")
        final = previous if failed else candidate
        if any((live / name).read_bytes() != final[name] for name in NAMES):
            raise RuntimeError("Final generation mismatch")
        return {"status": "recovered" if failed else "verified",
                "mode": "self-contained-disposable-filesystem-trial",
                "failure_checkpoint": fail_after, "journal_states": reached,
                "asset_count": len(NAMES), "production_installed": False,
                "systemd_started": False, "agent_enrolled": False,
                "external_network_requests_made": False,
                "temporary_artifacts_retained": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-after", choices=STAGES)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.fail_after), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
