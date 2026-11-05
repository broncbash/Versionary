"""Regression tests for interrupted atomic release staging."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_interruption", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseInterruption(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "versionary-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('original')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.original = atomic.stage_release(
            self.app, self.modules
        )
        atomic.activate_release(self.app, self.original)

        self.updated = {
            "__main__.py": b"print('updated')\n",
            "identity.py": b"IDENTITY = False\n",
        }

    def test_failed_stage_preserves_active_release(self):
        active = self.app / "agent"
        original_link = os.readlink(active)

        real_fsync = atomic.os.fsync
        calls = 0

        def interrupted_fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated interrupted write")
            return real_fsync(fd)

        with patch.object(
            atomic.os, "fsync",
            side_effect=interrupted_fsync,
        ):
            with self.assertRaises(OSError):
                atomic.stage_release(self.app, self.updated)

        self.assertEqual(os.readlink(active), original_link)
        self.assertEqual(
            (active / "identity.py").read_bytes(),
            self.modules["identity.py"],
        )

    def test_failed_stage_leaves_no_incomplete_release(self):
        real_fsync = atomic.os.fsync
        calls = 0

        def interrupted_fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated interrupted write")
            return real_fsync(fd)

        with patch.object(
            atomic.os, "fsync",
            side_effect=interrupted_fsync,
        ):
            with self.assertRaises(OSError):
                atomic.stage_release(self.app, self.updated)

        identifier = atomic.release_id(self.updated)
        release = self.app / "releases" / identifier

        self.assertFalse(release.exists())

        leftovers = list(
            (self.app / "releases").glob(".stage-*")
        )
        self.assertEqual(leftovers, [])

    def test_clean_retry_after_interruption(self):
        real_fsync = atomic.os.fsync
        calls = 0

        def interrupted_fsync(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated interrupted write")
            return real_fsync(fd)

        with patch.object(
            atomic.os, "fsync",
            side_effect=interrupted_fsync,
        ):
            with self.assertRaises(OSError):
                atomic.stage_release(self.app, self.updated)

        identifier = atomic.stage_release(
            self.app, self.updated
        )
        atomic.activate_release(self.app, identifier)

        self.assertEqual(
            (self.app / "agent/identity.py").read_bytes(),
            self.updated["identity.py"],
        )


if __name__ == "__main__":
    unittest.main()
