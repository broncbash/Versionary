"""Offline atomic configuration publication regression tests."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/setup-config.py"

spec = importlib.util.spec_from_file_location(
    "batch8_atomic_config",
    SOURCE,
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

SERVER = "https://patch.example.test"


class AtomicConfigurationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = (
            self.root / "etc/versionary-agent/config.json"
        )

    def install(self, server=SERVER):
        return installer.install_config(self.root, server)

    def pending(self):
        directory = self.target.parent
        if not directory.exists():
            return []
        return list(directory.glob(".config-install-*"))

    def test_initial_install(self):
        result = self.install()
        self.assertEqual(result["server"], SERVER)
        self.assertTrue(self.target.is_file())
        self.assertEqual(self.pending(), [])

    def test_idempotent_install_preserves_inode(self):
        self.install()
        before = self.target.stat().st_ino
        self.install()
        self.assertEqual(self.target.stat().st_ino, before)

    def test_conflicting_config_refused(self):
        self.install()
        original = self.target.read_bytes()

        with self.assertRaises(ValueError):
            self.install("https://different.example.test")

        self.assertEqual(self.target.read_bytes(), original)

    def test_write_failure_leaves_no_target(self):
        with patch.object(
            installer.os,
            "fsync",
            side_effect=OSError("Injected sync failure"),
        ):
            with self.assertRaises(OSError):
                self.install()

        self.assertFalse(self.target.exists())
        self.assertEqual(self.pending(), [])

    def test_publication_failure_cleans_temporary(self):
        with patch.object(
            installer.os,
            "link",
            side_effect=OSError("Injected publication failure"),
        ):
            with self.assertRaises(OSError):
                self.install()

        self.assertFalse(self.target.exists())
        self.assertEqual(self.pending(), [])

    def test_existing_symlink_refused(self):
        self.target.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.write_text("preserve")
        self.target.symlink_to(outside)

        with self.assertRaises(ValueError):
            self.install()

        self.assertEqual(outside.read_text(), "preserve")

    def test_existing_hardlink_refused(self):
        self.target.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.write_text("preserve")
        os.link(outside, self.target)

        with self.assertRaises(ValueError):
            self.install()

        self.assertEqual(outside.read_text(), "preserve")

    def test_directory_sync_failure_preserves_publication(self):
        original_sync = installer.os.fsync
        calls = []

        def fail_second_sync(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError("Injected directory sync failure")
            return original_sync(fd)

        with patch.object(
            installer.os,
            "fsync",
            side_effect=fail_second_sync,
        ):
            with self.assertRaises(OSError):
                self.install()

        self.assertTrue(self.target.is_file())
        self.assertEqual(self.pending(), [])
        self.install()


if __name__ == "__main__":
    unittest.main()
