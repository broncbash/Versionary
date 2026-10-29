"""Directory synchronization regression tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_durability", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseDurability(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('hello')\n",
            "identity.py": b"IDENTITY = True\n",
        }

    def test_staging_syncs_release_directories(self):
        events = []

        real_fsync = atomic.os.fsync
        real_rename = atomic.os.rename

        def observed_fsync(fd):
            import os
            import stat

            info = os.fstat(fd)

            if stat.S_ISDIR(info.st_mode):
                events.append("directory-sync")

            return real_fsync(fd)

        def observed_rename(source, destination):
            events.append("publish-release")
            return real_rename(source, destination)

        with (
            patch.object(
                atomic.os, "fsync",
                side_effect=observed_fsync,
            ),
            patch.object(
                atomic.os, "rename",
                side_effect=observed_rename,
            ),
        ):
            atomic.stage_release(self.app, self.modules)

        self.assertIn("publish-release", events)

        publish = events.index("publish-release")

        self.assertGreaterEqual(
            events[:publish].count("directory-sync"),
            2,
            "Stage directories must be synced before publication",
        )

        self.assertGreaterEqual(
            events[publish + 1:].count("directory-sync"),
            1,
            "Releases directory must be synced after publication",
        )

    def test_activation_syncs_application_directory(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        events = []

        real_fsync = atomic.os.fsync
        real_replace = atomic.os.replace

        def observed_fsync(fd):
            import os
            import stat

            info = os.fstat(fd)

            if stat.S_ISDIR(info.st_mode):
                events.append("directory-sync")

            return real_fsync(fd)

        def observed_replace(source, destination):
            events.append("activate-release")
            return real_replace(source, destination)

        with (
            patch.object(
                atomic.os, "fsync",
                side_effect=observed_fsync,
            ),
            patch.object(
                atomic.os, "replace",
                side_effect=observed_replace,
            ),
        ):
            atomic.activate_release(self.app, identifier)

        activate = events.index("activate-release")

        self.assertIn(
            "directory-sync",
            events[activate + 1:],
            "Application directory must be synced after activation",
        )


if __name__ == "__main__":
    unittest.main()
