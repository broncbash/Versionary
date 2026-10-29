"""Additional security tests for descriptor-relative file operations."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_secure_file_edges",
    ROOT / "installer/secure-files.py",
)

secure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secure)


class TestSecureFileEdgeCases(unittest.TestCase):

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

    def test_fifo_rejected_without_blocking(self):
        os.mkfifo(self.root / "pipe")

        with self.assertRaises(RuntimeError):
            secure.open_regular_file(self.fd, "pipe")

    def test_directory_rejected_as_regular_file(self):
        (self.root / "subdir").mkdir()

        with self.assertRaises(RuntimeError):
            secure.open_regular_file(self.fd, "subdir")

    def test_unsafe_creation_modes_rejected(self):
        for mode in (0o777, 0o666, 0o622, -1, 0o1000):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    secure.create_regular_file(
                        self.fd, "unsafe", mode=mode
                    )

        self.assertFalse((self.root / "unsafe").exists())

    def test_exact_created_file_permissions(self):
        fd = secure.create_regular_file(
            self.fd, "module.py", mode=0o644
        )

        os.close(fd)

        self.assertEqual(
            stat.S_IMODE(
                (self.root / "module.py").stat().st_mode
            ),
            0o644,
        )

    def test_existing_file_preserved_on_collision(self):
        path = self.root / "existing.py"
        path.write_bytes(b"ORIGINAL")

        with self.assertRaises(FileExistsError):
            secure.create_regular_file(
                self.fd, "existing.py", mode=0o600
            )

        self.assertEqual(path.read_bytes(), b"ORIGINAL")


if __name__ == "__main__":
    unittest.main()
