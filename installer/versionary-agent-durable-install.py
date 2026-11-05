#!/usr/bin/env python3
"""Durable, isolated-root Versionary installation prototype.

Writes an installation-intent journal before publishing files.
An interrupted installation remains blocked pending inspection.
No production installation, automatic rollback, service activation,
enrollment, or unattended recovery is supported.
"""

import hashlib
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOURNAL = ".versionary-durable-install.json"
VERSION = 1


class RecoveryRequired(RuntimeError):
    pass


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, HERE / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sync_directory(path):
    fd = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_root(root):
    root = Path(root)

    if not root.is_absolute() or root == Path("/"):
        raise ValueError("Isolated absolute root required")

    info = root.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Unsafe installation root")

    if info.st_uid != os.geteuid():
        raise ValueError("Unexpected root owner")

    if info.st_mode & 0o022:
        raise ValueError("Writable installation root")

    return root


def validate_payloads(payloads):
    journal = load(
        "versionary-agent-system-journal.py",
        "versionary88_journal",
    )
    return journal.make_journal(payloads)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def journal_path(root):
    return Path(root) / JOURNAL


def write_intent(root, payloads):
    root = validate_root(root)
    intent = validate_payloads(payloads)
    path = journal_path(root)

    data = {
        "version": VERSION,
        "phase": "installing",
        "files": intent["files"],
    }

    encoded = (
        json.dumps(data, sort_keys=True, indent=2) + "\n"
    ).encode()

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL |
        getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(root)
    except Exception:
        # Do not silently discard a potentially durable intent.
        raise

    return data


def read_intent(root):
    root = validate_root(root)
    path = journal_path(root)
    info = path.lstat()

    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_nlink != 1
        or info.st_mode & 0o077
        or info.st_size <= 0
        or info.st_size > 1024 * 1024
    ):
        raise ValueError("Unsafe recovery journal")

    data = json.loads(path.read_bytes())

    if (
        not isinstance(data, dict)
        or data.get("version") != VERSION
        or data.get("phase") != "installing"
        or not isinstance(data.get("files"), dict)
        or not data["files"]
    ):
        raise ValueError("Unsupported recovery journal")

    journal = load(
        "versionary-agent-system-journal.py",
        "versionary88_read",
    )

    for relative, entry in data["files"].items():
        journal.validate_relative(relative)
        if (
            not isinstance(entry, dict)
            or entry.get("state") != "planned"
            or not isinstance(entry.get("size"), int)
            or isinstance(entry["size"], bool)
            or entry["size"] < 0
            or not isinstance(entry.get("sha256"), str)
            or len(entry["sha256"]) != 64
            or any(
                c not in "0123456789abcdef"
                for c in entry["sha256"]
            )
        ):
            raise ValueError("Invalid recovery journal entry")

    return data


def inspect(root):
    root = validate_root(root)
    path = journal_path(root)

    try:
        path.lstat()
    except FileNotFoundError:
        return {
            "status": "clear",
            "files": {},
            "installation_performed": False,
        }

    data = read_intent(root)
    journal = load(
        "versionary-agent-system-journal.py",
        "versionary88_inspect",
    )

    states = journal.inspect_recovery(
        root,
        {
            "version": 1,
            "status": "planned",
            "files": data["files"],
        },
    )

    return {
        "status": "recovery_required",
        "files": states,
        "all_present": all(
            state == "matches"
            for state in states.values()
        ),
        "installation_performed": False,
    }


def verify_expected(root, payloads):
    root = validate_root(root)
    data = read_intent(root)
    expected = validate_payloads(payloads)

    if data["files"] != expected["files"]:
        raise ValueError(
            "Recovery payload manifest mismatch"
        )

    result = inspect(root)

    if not result["all_present"]:
        raise RecoveryRequired(
            "Incomplete installation requires review"
        )

    return result


def finalize(root, payloads):
    """Clear intent only after every expected file is verified."""
    root = validate_root(root)
    verify_expected(root, payloads)

    path = journal_path(root)
    info = path.lstat()

    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o077
    ):
        raise ValueError("Unsafe journal before finalize")

    path.unlink()
    sync_directory(root)

    return {
        "status": "complete",
        "verified_files": len(payloads),
        "services_activated": False,
        "enrollment_performed": False,
        "production_approved": False,
    }


def install_isolated(root, payloads, modes=None,
                     fail_after=None):
    """Install using durable intent and an existing transaction.

    Ordinary failures and interruptions intentionally leave the
    journal in place for explicit inspection.
    """
    root = validate_root(root)

    if inspect(root)["status"] != "clear":
        raise RecoveryRequired(
            "Existing recovery journal blocks installation"
        )

    validate_payloads(payloads)

    transaction = load(
        "versionary-agent-system-transaction.py",
        "versionary88_transaction",
    )

    # Reject unsafe destinations before writing the journal.
    for relative, content in payloads.items():
        path = transaction._relative(relative)
        transaction._check_parent_chain(root, path)
        transaction._existing_file(root / path, content)

    write_intent(root, payloads)

    result = transaction.install_payloads(
        root,
        payloads,
        modes=modes,
        fail_after=fail_after,
    )

    completed = finalize(root, payloads)
    completed.update(result)
    completed["root"] = str(root)
    completed["globally_atomic"] = False
    completed["real_system_installation_enabled"] = False
    return completed


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--inspect", action="store_true"
    )
    args = parser.parse_args()

    if not args.inspect:
        parser.error(
            "CLI is inspection-only; installation is API-only"
        )

    try:
        result = inspect(args.root)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"[STOP] {exc}\n")

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "clear" else 1


if __name__ == "__main__":
    raise SystemExit(main())
