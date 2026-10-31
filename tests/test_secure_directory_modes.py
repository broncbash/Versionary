"""Permission-mode tests for secure directory traversal."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_secure_directory_modes",
    ROOT / "installer/secure-directories.py",
)

secure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secure)


class TestSecureDirectoryModes(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)

    def test_private_directory_created_with_0700(self):
        with secure.secure_directory(
            self.root,
            "var/lib/versionary-agent",
            create=True,
            mode=0o700,
        ):
            pass

        directory = self.root / "var/lib/versionary-agent"

        self.assertEqual(
            stat.S_IMODE(directory.stat().st_mode),
            0o700,
        )

    def test_application_directory_created_with_0755(self):
        with secure.secure_directory(
            self.root,
            "opt/versionary-agent",
            create=True,
            mode=0o755,
        ):
            pass

        directory = self.root / "opt/versionary-agent"

        self.assertEqual(
            stat.S_IMODE(directory.stat().st_mode),
            0o755,
        )

    def test_existing_private_directory_preserved(self):
        directory = self.root / "state"
        directory.mkdir(mode=0o700)

        with secure.secure_directory(
            self.root,
            "state",
            create=True,
            mode=0o755,
        ):
            pass

        self.assertEqual(
            stat.S_IMODE(directory.stat().st_mode),
            0o700,
        )

    def test_existing_directory_not_chmodded(self):
        directory = self.root / "config"
        directory.mkdir(mode=0o750)
        directory.chmod(0o750)

        with secure.secure_directory(
            self.root,
            "config",
            create=True,
            mode=0o755,
        ):
            pass

        self.assertEqual(
            stat.S_IMODE(directory.stat().st_mode),
            0o750,
        )

    def test_invalid_directory_mode_rejected(self):
        for mode in (0o777, 0o775, -1):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    with secure.secure_directory(
                        self.root,
                        "invalid",
                        create=True,
                        mode=mode,
                    ):
                        pass

    def test_descriptor_remains_valid_inside_context(self):
        with secure.secure_directory(
            self.root,
            "private",
            create=True,
            mode=0o700,
        ) as fd:
            self.assertTrue(
                stat.S_ISDIR(os.fstat(fd).st_mode)
            )


if __name__ == "__main__":
    unittest.main()
