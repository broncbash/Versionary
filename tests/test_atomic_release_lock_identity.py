"""Regression tests for installer lock-file identity."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_lock_identity", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseLockIdentity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "versionary-agent"
        self.app.mkdir()

    def test_lock_path_identity_preserved(self):
        lock = self.app / ".install.lock"

        with atomic.install_lock(self.app):
            original = lock.stat()

            self.assertEqual(original.st_nlink, 1)

            self.assertTrue(lock.is_file())

            current = lock.stat()

            self.assertEqual(
                (original.st_dev, original.st_ino),
                (current.st_dev, current.st_ino),
            )

    def test_replaced_lock_path_detected(self):
        lock = self.app / ".install.lock"

        with self.assertRaises(RuntimeError):
            with atomic.install_lock(self.app):
                original = lock.stat()

                lock.unlink()
                lock.write_bytes(b"replacement")

                current = lock.stat()

                self.assertNotEqual(
                    (original.st_dev, original.st_ino),
                    (current.st_dev, current.st_ino),
                )

    def test_lock_file_is_not_world_writable(self):
        lock = self.app / ".install.lock"

        with atomic.install_lock(self.app):
            mode = lock.stat().st_mode & 0o777

            self.assertEqual(mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
