"""Descriptor-relative installer locking security tests."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_secure_install_lock",
    ROOT / "installer/secure-install-lock.py",
)


class TestSecureInstallLock(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.root.chmod(0o700)

        self.fd = os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )

    def tearDown(self):
        os.close(self.fd)

    def load_helper(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_lock_created_with_private_permissions(self):
        secure = self.load_helper()

        with secure.install_lock_fd(self.fd):
            info = (self.root / ".install.lock").stat()
            self.assertEqual(info.st_mode & 0o777, 0o600)

    def test_existing_lock_reused(self):
        secure = self.load_helper()

        with secure.install_lock_fd(self.fd):
            first = (self.root / ".install.lock").stat().st_ino

        with secure.install_lock_fd(self.fd):
            second = (self.root / ".install.lock").stat().st_ino

        self.assertEqual(first, second)

    def test_symlinked_lock_rejected(self):
        secure = self.load_helper()

        target = self.root / "target"
        target.write_text("protected")

        (self.root / ".install.lock").symlink_to(target)

        with self.assertRaises(OSError):
            with secure.install_lock_fd(self.fd):
                pass

        self.assertEqual(target.read_text(), "protected")

    def test_hardlinked_lock_rejected(self):
        secure = self.load_helper()

        target = self.root / "target"
        target.write_text("protected")

        os.link(target, self.root / ".install.lock")

        with self.assertRaises(RuntimeError):
            with secure.install_lock_fd(self.fd):
                pass

    def test_world_writable_lock_rejected(self):
        secure = self.load_helper()

        lock = self.root / ".install.lock"
        lock.write_text("unsafe")
        lock.chmod(0o666)

        with self.assertRaises(RuntimeError):
            with secure.install_lock_fd(self.fd):
                pass

    def test_replaced_lock_detected(self):
        secure = self.load_helper()

        with self.assertRaises(RuntimeError):
            with secure.install_lock_fd(self.fd):
                os.unlink(
                    ".install.lock",
                    dir_fd=self.fd,
                )

                replacement = os.open(
                    ".install.lock",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=self.fd,
                )
                os.close(replacement)


if __name__ == "__main__":
    unittest.main()
