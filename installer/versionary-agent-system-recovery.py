#!/usr/bin/env python3
"""Conservative isolated-root installation recovery coordinator.

No automatic deletion of journal-listed payloads.
Not authorized for real-system installation.
"""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name,
        HERE / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_pending(root):
    journal_module = load(
        "versionary-agent-system-journal.py",
        "versionary_recovery_journal",
    )

    journal_path = Path(root) / journal_module.JOURNAL_NAME

    if not journal_path.is_file() and not journal_path.is_symlink():
        return {"status": "clear", "files": {}}

    journal = journal_module.read_journal(root)
    files = journal_module.inspect_recovery(root, journal)

    return {
        "status": "recovery_required",
        "files": files,
    }


def install_isolated(root, payloads, modes=None, fail_after=None):
    root = Path(root)

    if not root.is_absolute() or root == Path("/"):
        raise ValueError("Isolated root required")

    pending = inspect_pending(root)

    if pending["status"] != "clear":
        raise RuntimeError(
            "Pending installation journal requires review"
        )

    journal_module = load(
        "versionary-agent-system-journal.py",
        "versionary_install_journal",
    )
    transaction = load(
        "versionary-agent-system-transaction.py",
        "versionary_install_transaction",
    )

    journal = journal_module.make_journal(payloads)
    journal_path = journal_module.write_journal(root, journal)

    try:
        result = transaction.install_payloads(
            root,
            payloads,
            modes=modes,
            fail_after=fail_after,
        )
    except Exception:
        # Keep the journal for review. Never assume that a
        # failed transaction fully restored the original state.
        raise

    journal_path.unlink()

    return result


def review_and_clear(root, payloads):
    """Clear a pending journal only when no installation files remain.

    Existing matching files are deliberately not deleted. If any
    journal-listed file exists, manual review is required.
    """
    root = Path(root)
    if not root.is_absolute() or root == Path("/") or root.is_symlink():
        raise ValueError("Isolated root required")

    journal_module = load(
        "versionary-agent-system-journal.py",
        "versionary_clear_journal",
    )
    journal = journal_module.read_journal(root)

    expected = journal_module.make_journal(payloads)
    if journal["files"] != expected["files"]:
        raise ValueError("Journal does not match requested payload")

    results = journal_module.inspect_recovery(root, journal)
    if any(state != "absent" for state in results.values()):
        raise RuntimeError(
            "Existing installation files require manual review"
        )

    journal_path = root / journal_module.JOURNAL_NAME
    info = journal_path.lstat()
    if info.st_nlink != 1 or info.st_mode & 0o077:
        raise ValueError("Unsafe journal")

    journal_path.unlink()
    return {"status": "cleared", "files_removed": 0}
