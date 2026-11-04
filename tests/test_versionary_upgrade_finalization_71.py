"""Read-only upgrade finalization assessment regression tests."""

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
    "versionary_71_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_71_upgrade",
)


class FinalizationAssessmentTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-finalization71-"
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

    def test_no_transaction_is_not_cleanup_authorization(self):
        result = upgrade.finalization_assessment(
            self.root
        )

        self.assertEqual(
            result["status"], "no_transaction"
        )
        self.assertFalse(result["eligible_for_review"])
        self.assertFalse(result["cleanup_authorized"])

    def test_applied_upgrade_requires_recovery(self):
        upgrade.apply(
            self.root, self.old, self.new
        )

        result = upgrade.finalization_assessment(
            self.root
        )

        self.assertEqual(
            result["status"],
            "recovery_or_investigation_required",
        )
        self.assertFalse(result["eligible_for_review"])
        self.assertFalse(result["cleanup_authorized"])

    def test_restored_upgrade_is_review_candidate(self):
        upgrade.apply(
            self.root, self.old, self.new
        )
        upgrade.recover_to_old(self.root)

        tx = upgrade.transaction_path(self.root)

        before = sorted(p.name for p in tx.iterdir())

        result = upgrade.finalization_assessment(
            self.root
        )

        after = sorted(p.name for p in tx.iterdir())

        self.assertEqual(
            result["status"], "review_candidate"
        )
        self.assertTrue(result["eligible_for_review"])
        self.assertFalse(result["cleanup_authorized"])
        self.assertEqual(before, after)
        self.assertTrue(tx.exists())

        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "recovery_required",
        )

    def test_unexpected_journal_entry_blocks_review(self):
        upgrade.apply(
            self.root, self.old, self.new
        )
        upgrade.recover_to_old(self.root)

        tx = upgrade.transaction_path(self.root)
        (tx / "unexpected-file").write_bytes(b"evidence")

        result = upgrade.finalization_assessment(
            self.root
        )

        self.assertEqual(
            result["status"],
            "recovery_or_investigation_required",
        )
        self.assertFalse(result["eligible_for_review"])
        self.assertFalse(result["cleanup_authorized"])
        self.assertEqual(
            result["unexpected_entries"],
            ["unexpected-file"],
        )
        self.assertTrue(
            (tx / "unexpected-file").exists()
        )

    def test_partial_upgrade_blocks_review(self):
        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root,
                self.old,
                self.new,
                fail_after=1,
            )

        result = upgrade.finalization_assessment(
            self.root
        )

        self.assertFalse(result["eligible_for_review"])
        self.assertFalse(result["cleanup_authorized"])


if __name__ == "__main__":
    unittest.main()
