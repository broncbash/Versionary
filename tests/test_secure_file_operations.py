"""Tests for descriptor-relative secure file operations."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_secure_files",
    ROOT / "installer/secure-files.py",
)


class TestSecureFileOperations(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.root.chmod(0o700)

        self.directory_fd = os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )

    def tearDown(self):
        os.close(self.directory_fd)

    def load_helper(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_create_exclusive_regular_file(self):
        secure = self.load_helper()

        fd = secure.create_regular_file(
            self.directory_fd,
            "module.py",
            mode=0o600,
        )

        try:
            os.write(fd, b"print('hello')\n")
        finally:
            os.close(fd)

        self.assertEqual(
            (self.root / "module.py").read_bytes(),
            b"print('hello')\n",
        )

    def test_existing_file_not_overwritten(self):
        secure = self.load_helper()

        (self.root / "existing.py").write_text("original")

        with self.assertRaises(FileExistsError):
            secure.create_regular_file(
                self.directory_fd,
                "existing.py",
            )

        self.assertEqual(
            (self.root / "existing.py").read_text(),
            "original",
        )

    def test_symlink_not_followed(self):
        secure = self.load_helper()

        target = self.root / "target"
        target.write_text("protected")

        (self.root / "link").symlink_to(target)

        with self.assertRaises(OSError):
            secure.open_regular_file(
                self.directory_fd,
                "link",
            )

        self.assertEqual(target.read_text(), "protected")

    def test_path_traversal_rejected(self):
        secure = self.load_helper()

        for name in ("../escape", "/tmp/escape", "a/b", ".", ".."):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    secure.create_regular_file(
                        self.directory_fd,
                        name,
                    )

    def test_hardlinked_file_rejected(self):
        secure = self.load_helper()

        original = self.root / "original"
        original.write_text("data")

        os.link(original, self.root / "linked")

        with self.assertRaises(RuntimeError):
            secure.open_regular_file(
                self.directory_fd,
                "linked",
            )

    def test_world_writable_file_rejected(self):
        secure = self.load_helper()

        path = self.root / "unsafe"
        path.write_text("data")
        path.chmod(0o666)

        with self.assertRaises(RuntimeError):
            secure.open_regular_file(
                self.directory_fd,
                "unsafe",
            )


if __name__ == "__main__":
    unittest.main()
