"""Recovery integration tests for isolated Versionary installations."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-recovery.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_recovery",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RecoveryIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.payloads = {
            "etc/versionary-agent/config.json": b"config",
            "etc/versionary-agent/ca.crt": b"certificate",
        }

    def test_clean_root_has_no_pending_recovery(self):
        result = module.inspect_pending(self.root)
        self.assertEqual(result["status"], "clear")

    def test_successful_install_clears_journal(self):
        result = module.install_isolated(
            self.root,
            self.payloads,
        )

        self.assertEqual(result["created"], 2)
        self.assertEqual(
            module.inspect_pending(self.root)["status"],
            "clear",
        )

    def test_failed_install_preserves_journal(self):
        with self.assertRaises(RuntimeError):
            module.install_isolated(
                self.root,
                self.payloads,
                fail_after=1,
            )

        result = module.inspect_pending(self.root)
        self.assertEqual(
            result["status"],
            "recovery_required",
        )

    def test_pending_journal_blocks_retry(self):
        with self.assertRaises(RuntimeError):
            module.install_isolated(
                self.root,
                self.payloads,
                fail_after=1,
            )

        with self.assertRaisesRegex(
            RuntimeError,
            "Pending installation journal",
        ):
            module.install_isolated(
                self.root,
                self.payloads,
            )

    def test_existing_identical_file_preserved(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"config")

        result = module.install_isolated(
            self.root,
            self.payloads,
        )

        self.assertEqual(result["preserved"], 1)
        self.assertEqual(target.read_bytes(), b"config")

    def test_modified_recovery_target_rejected(self):
        with self.assertRaises(RuntimeError):
            module.install_isolated(
                self.root,
                self.payloads,
                fail_after=1,
            )

        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"unexpected")

        with self.assertRaises(ValueError):
            module.inspect_pending(self.root)


if __name__ == "__main__":
    unittest.main()
