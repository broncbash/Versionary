"""Fail-closed upgrade journal integrity checks."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    "versionary-agent-isolated-coordinator.py",
    "versionary_72_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_72_upgrade",
)


class JournalIntegrityTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-journal72-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.old = {
            name: f"old:{name}".encode()
            for name in coordinator.MODES
        }
        self.new = {
            name: f"new:{name}".encode()
            for name in coordinator.MODES
        }

        coordinator.install_payloads_isolated(
            self.root, self.old
        )
        upgrade.apply(
            self.root, self.old, self.new
        )
        upgrade.recover_to_old(self.root)

        self.tx = upgrade.transaction_path(self.root)

    def assess(self):
        return upgrade.finalization_assessment(
            self.root
        )

    def assert_blocked(self, result):
        self.assertFalse(
            result["eligible_for_review"]
        )
        self.assertFalse(
            result["cleanup_authorized"]
        )
        self.assertTrue(self.tx.exists())
        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "recovery_required",
        )

    def test_intact_restored_journal_is_candidate(self):
        result = self.assess()
        self.assertEqual(
            result["status"], "review_candidate"
        )
        self.assertTrue(
            result["eligible_for_review"]
        )
        self.assertFalse(
            result["cleanup_authorized"]
        )

    def test_unexpected_file_blocks_review(self):
        (self.tx / "unrecognized").write_bytes(
            b"unexpected"
        )
        result = self.assess()
        self.assert_blocked(result)
        self.assertEqual(
            result["unexpected_entries"],
            ["unrecognized"],
        )

    def test_unexpected_directory_blocks_review(self):
        (self.tx / "unexpected-dir").mkdir()
        result = self.assess()
        self.assert_blocked(result)
        self.assertIn(
            "unexpected-dir",
            result["unexpected_entries"],
        )

    def test_unexpected_symlink_blocks_review(self):
        (self.tx / "unexpected-link").symlink_to(
            "/nonexistent-versionary-target"
        )
        result = self.assess()
        self.assert_blocked(result)
        self.assertIn(
            "unexpected-link",
            result["unexpected_entries"],
        )

    def test_missing_snapshot_blocks_review(self):
        (self.tx / "old-000").unlink()
        result = self.assess()
        self.assert_blocked(result)
        self.assertEqual(
            result["missing_entries"],
            ["old-000"],
        )

    def test_missing_manifest_blocks_review(self):
        (self.tx / "manifest.json").unlink()
        result = self.assess()
        self.assert_blocked(result)
        self.assertEqual(
            result["missing_entries"],
            ["manifest.json"],
        )

    def test_tampered_snapshot_rejected(self):
        snapshot = self.tx / "old-000"
        snapshot.write_bytes(b"tampered")

        with self.assertRaises(ValueError):
            self.assess()

        self.assertTrue(self.tx.exists())

    def test_snapshot_symlink_rejected(self):
        snapshot = self.tx / "old-000"
        snapshot.unlink()
        snapshot.symlink_to(
            "/nonexistent-versionary-target"
        )

        with self.assertRaises(
            (ValueError, FileNotFoundError)
        ):
            self.assess()

        self.assertTrue(self.tx.exists())


if __name__ == "__main__":
    unittest.main()
