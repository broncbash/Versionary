"""Batch 85: isolated recovery authorization boundaries."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "installer/versionary-agent-system-recovery.py"

spec = importlib.util.spec_from_file_location(
    "versionary_recovery85", SOURCE
)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryBoundaryTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory(
            prefix="versionary-recovery85-"
        )
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.payloads = {
            "etc/versionary-agent/test.conf": b"test\n"
        }

    def test_rejects_real_root_for_install(self):
        with self.assertRaises(ValueError):
            recovery.install_isolated("/", self.payloads)

    def test_rejects_relative_root_for_install(self):
        with self.assertRaises(ValueError):
            recovery.install_isolated(
                "relative", self.payloads
            )

    def test_rejects_real_root_for_clear(self):
        with self.assertRaises(ValueError):
            recovery.review_and_clear("/", self.payloads)

    def test_rejects_relative_root_for_clear(self):
        with self.assertRaises(ValueError):
            recovery.review_and_clear(
                "relative", self.payloads
            )

    def test_rejects_symlink_root_for_clear(self):
        link = self.root.parent / (
            self.root.name + "-recovery-link"
        )
        link.symlink_to(
            self.root, target_is_directory=True
        )
        self.addCleanup(link.unlink)

        with self.assertRaises(ValueError):
            recovery.review_and_clear(
                link, self.payloads
            )

    def test_pending_journal_blocks_install(self):
        with patch.object(
            recovery,
            "inspect_pending",
            return_value={
                "status": "recovery_required",
                "files": {},
            },
        ):
            with self.assertRaises(RuntimeError):
                recovery.install_isolated(
                    self.root, self.payloads
                )

    def test_clear_never_deletes_existing_payload(self):
        journal = recovery.load(
            "versionary-agent-system-journal.py",
            "versionary_recovery85_journal",
        )
        journal.write_journal(
            self.root,
            journal.make_journal(self.payloads),
        )

        target = (
            self.root /
            "etc/versionary-agent/test.conf"
        )
        target.parent.mkdir(parents=True)
        target.write_bytes(b"test\n")

        with self.assertRaises(RuntimeError):
            recovery.review_and_clear(
                self.root, self.payloads
            )

        self.assertEqual(target.read_bytes(), b"test\n")

    def test_clear_absent_payload_preserves_unrelated(self):
        journal = recovery.load(
            "versionary-agent-system-journal.py",
            "versionary_recovery85_journal2",
        )
        journal.write_journal(
            self.root,
            journal.make_journal(self.payloads),
        )

        unrelated = self.root / "preserve.txt"
        unrelated.write_text("keep\n")

        result = recovery.review_and_clear(
            self.root, self.payloads
        )

        self.assertEqual(result["status"], "cleared")
        self.assertEqual(unrelated.read_text(), "keep\n")
        self.assertFalse(
            (
                self.root / journal.JOURNAL_NAME
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
