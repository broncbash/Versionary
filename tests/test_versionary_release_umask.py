"""Regression coverage for secure Versionary release directories."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "installer/atomic-release.py"


def load_atomic_release():
    spec = importlib.util.spec_from_file_location(
        "versionary_umask_atomic_release",
        MODULE,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VersionaryReleaseUmaskTests(unittest.TestCase):

    @staticmethod
    def modules():
        return {
            "__main__.py": b"print('versionary test')\n",
            "config.py": b"SERVER = 'test'\n",
        }

    def install_with_umask(self, mask):
        atomic = load_atomic_release()

        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "versionary-agent"
            app.mkdir(mode=0o700)

            previous = os.umask(mask)
            try:
                identifier = atomic.install_release(
                    app,
                    self.modules(),
                )
            finally:
                os.umask(previous)

            releases = app / "releases"
            release = releases / identifier

            self.assertTrue(release.is_dir())
            self.assertEqual(
                stat.S_IMODE(releases.stat().st_mode) & 0o022,
                0,
            )
            self.assertTrue((release / "agent").is_dir())
            self.assertTrue((app / "agent").is_symlink())

    def test_group_writable_default_umask(self):
        self.install_with_umask(0o002)

    def test_standard_default_umask(self):
        self.install_with_umask(0o022)

    def test_existing_unsafe_directory_is_rejected(self):
        atomic = load_atomic_release()

        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "versionary-agent"
            app.mkdir(mode=0o700)

            releases = app / "releases"
            releases.mkdir(mode=0o700)
            releases.chmod(0o775)

            with self.assertRaisesRegex(
                RuntimeError,
                "Unsafe permissions",
            ):
                atomic.install_release(
                    app,
                    self.modules(),
                )

            self.assertEqual(
                stat.S_IMODE(releases.stat().st_mode),
                0o775,
            )


if __name__ == "__main__":
    unittest.main()
