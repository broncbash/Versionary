"""Isolated transaction tests for Versionary agent installation."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-transaction.py"

spec = importlib.util.spec_from_file_location(
    "versionary_system_transaction",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemTransactionTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_creates_multiple_files(self):
        result = module.install_payloads(
            self.root,
            {
                "etc/versionary-agent/config.json": b"config",
                "etc/versionary-agent/ca.crt": b"ca",
            },
        )

        self.assertEqual(result["created"], 2)
        self.assertEqual(
            (self.root / "etc/versionary-agent/config.json").read_bytes(),
            b"config",
        )

    def test_idempotent_installation(self):
        payload = {"etc/versionary-agent/config.json": b"config"}

        module.install_payloads(self.root, payload)
        result = module.install_payloads(self.root, payload)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["preserved"], 1)

    def test_conflicting_file_rejected_without_modification(self):
        target = self.root / "etc/versionary-agent/config.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"original")

        with self.assertRaises(module.InstallationConflict):
            module.install_payloads(
                self.root,
                {"etc/versionary-agent/config.json": b"new"},
            )

        self.assertEqual(target.read_bytes(), b"original")

    def test_symlinked_parent_rejected(self):
        (self.root / "etc").symlink_to(self.root)

        with self.assertRaises(module.InstallationConflict):
            module.install_payloads(
                self.root,
                {"etc/versionary-agent/config.json": b"config"},
            )

    def test_symlinked_file_rejected(self):
        target = self.root / "config"
        target.symlink_to(self.root)

        with self.assertRaises(module.InstallationConflict):
            module.install_payloads(
                self.root,
                {"config": b"config"},
            )

    def test_hardlinked_file_rejected(self):
        target = self.root / "config"
        target.write_bytes(b"config")
        (self.root / "copy").hardlink_to(target)

        with self.assertRaises(module.InstallationConflict):
            module.install_payloads(
                self.root,
                {"config": b"config"},
            )

    def test_rolls_back_after_injected_failure(self):
        payload = {
            "etc/versionary-agent/config.json": b"config",
            "etc/versionary-agent/ca.crt": b"ca",
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "Injected",
        ):
            module.install_payloads(
                self.root,
                payload,
                fail_after=1,
            )

        self.assertFalse(
            (self.root / "etc/versionary-agent/config.json").exists()
        )
        self.assertFalse(
            (self.root / "etc/versionary-agent/ca.crt").exists()
        )

    def test_preserves_existing_file_on_rollback(self):
        existing = self.root / "existing"
        existing.write_bytes(b"same")

        with self.assertRaises(RuntimeError):
            module.install_payloads(
                self.root,
                {
                    "existing": b"same",
                    "new-a": b"a",
                    "new-b": b"b",
                },
                fail_after=1,
            )

        self.assertEqual(existing.read_bytes(), b"same")
        self.assertFalse((self.root / "new-a").exists())

    def test_rejects_system_root(self):
        with self.assertRaises(ValueError):
            module.install_payloads(
                Path("/"),
                {"tmp/versionary": b"test"},
            )


if __name__ == "__main__":
    unittest.main()
