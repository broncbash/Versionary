"""Failure injection and safety tests for isolated installation."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-transaction.py"

spec = importlib.util.spec_from_file_location(
    "versionary_transaction_hardening",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TransactionHardeningTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def payload(self):
        return {
            "etc/versionary-agent/config.json": b"config",
            "etc/versionary-agent/ca.crt": b"certificate",
        }

    def test_staging_failure_removes_staged_files(self):
        with self.assertRaisesRegex(RuntimeError, "staging"):
            module.install_payloads(
                self.root,
                self.payload(),
                fail_staging_after=1,
            )

        self.assertEqual(
            list(self.root.rglob(".versionary-stage-*")),
            [],
        )

    def test_staging_failure_removes_created_directories(self):
        with self.assertRaises(RuntimeError):
            module.install_payloads(
                self.root,
                self.payload(),
                fail_staging_after=1,
            )

        self.assertFalse((self.root / "etc").exists())

    def test_publication_failure_removes_created_files(self):
        with self.assertRaisesRegex(RuntimeError, "installation"):
            module.install_payloads(
                self.root,
                self.payload(),
                fail_after=1,
            )

        self.assertFalse(
            (self.root / "etc/versionary-agent/config.json").exists()
        )
        self.assertFalse(
            (self.root / "etc/versionary-agent/ca.crt").exists()
        )

    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            module.install_payloads(
                self.root,
                {"../outside": b"unsafe"},
            )

    def test_rejects_noncanonical_relative_path(self):
        with self.assertRaises(ValueError):
            module.install_payloads(
                self.root,
                {"etc//versionary-agent/config": b"unsafe"},
            )

    def test_rejects_symlinked_root(self):
        link = self.root.parent / (self.root.name + "-link")
        link.symlink_to(self.root)
        self.addCleanup(link.unlink)

        with self.assertRaises(ValueError):
            module.install_payloads(
                link,
                {"config": b"unsafe"},
            )

    def test_destination_appearing_during_publication_is_preserved(self):
        original_link = module.os.link

        def competing_link(source, destination, **kwargs):
            destination = Path(destination)
            destination.write_bytes(b"external")
            return original_link(source, destination, **kwargs)

        with patch.object(module.os, "link", side_effect=competing_link):
            with self.assertRaises(module.InstallationConflict):
                module.install_payloads(
                    self.root,
                    {"config": b"versionary"},
                )

        self.assertEqual(
            (self.root / "config").read_bytes(),
            b"external",
        )

    def test_successful_installation_remains_idempotent(self):
        first = module.install_payloads(self.root, self.payload())
        second = module.install_payloads(self.root, self.payload())

        self.assertEqual(first["created"], 2)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["preserved"], 2)


if __name__ == "__main__":
    unittest.main()
