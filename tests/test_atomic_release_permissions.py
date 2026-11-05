"""Filesystem permission regression tests for atomic releases."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_permissions", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleasePermissions(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / "versionary-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('hello')\n",
            "identity.py": b"IDENTITY = True\n",
        }

    def test_world_writable_app_rejected(self):
        self.app.chmod(0o777)

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_group_writable_releases_rejected(self):
        releases = self.app / "releases"
        releases.mkdir()
        releases.chmod(0o775)

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_world_writable_existing_release_rejected(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        release = self.app / "releases" / identifier
        release.chmod(0o777)

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_world_writable_existing_module_rejected(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        module = (
            self.app / "releases"
            / identifier / "agent/identity.py"
        )
        module.chmod(0o666)

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_unsafe_permissions_block_activation(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        release = self.app / "releases" / identifier
        release.chmod(0o777)

        with self.assertRaises(RuntimeError):
            atomic.activate_release(self.app, identifier)

        self.assertFalse((self.app / "agent").is_symlink())


if __name__ == "__main__":
    unittest.main()
