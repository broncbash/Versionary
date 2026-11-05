"""Tests for descriptor-based secure directory traversal."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_secure_directories",
    ROOT / "installer/secure-directories.py",
)

secure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secure)


class TestSecureDirectoryTraversal(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)

    def test_create_nested_directories(self):
        with secure.secure_directory(
            self.root, "opt/versionary-agent", create=True
        ) as fd:
            self.assertTrue(os.fstat(fd).st_mode)

        self.assertTrue(
            (self.root / "opt/versionary-agent").is_dir()
        )

    def test_existing_directory_accepted(self):
        (self.root / "opt").mkdir(mode=0o755)

        with secure.secure_directory(
            self.root, "opt", create=False
        ):
            pass

    def test_symlinked_parent_rejected(self):
        actual = self.root / "actual"
        actual.mkdir()

        (self.root / "opt").symlink_to(
            actual, target_is_directory=True
        )

        with self.assertRaises(OSError):
            with secure.secure_directory(
                self.root, "opt/agent", create=True
            ):
                pass

    def test_group_writable_parent_rejected(self):
        parent = self.root / "opt"
        parent.mkdir()
        parent.chmod(0o775)

        with self.assertRaises(RuntimeError):
            with secure.secure_directory(
                self.root, "opt/agent", create=True
            ):
                pass

    def test_world_writable_parent_rejected(self):
        parent = self.root / "opt"
        parent.mkdir()
        parent.chmod(0o777)

        with self.assertRaises(RuntimeError):
            with secure.secure_directory(
                self.root, "opt/agent", create=True
            ):
                pass

    def test_path_escape_rejected(self):
        for path in ("../escape", "/tmp/escape"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    with secure.secure_directory(
                        self.root, path, create=True
                    ):
                        pass

    def test_missing_directory_rejected_without_create(self):
        with self.assertRaises(FileNotFoundError):
            with secure.secure_directory(
                self.root, "missing", create=False
            ):
                pass


if __name__ == "__main__":
    unittest.main()
