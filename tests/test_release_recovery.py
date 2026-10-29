"""Recovery marker persistence, tampering, and restoration tests."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recovery = load("release-recovery.py", "test_release_recovery")
atomic = load("atomic-release.py", "test_recovery_atomic")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "opt/arby-patch-agent"
        self.app.mkdir(parents=True)
        self.previous = "a" * 64
        self.candidate = "b" * 64

    def test_marker_survives_new_read_and_clears(self):
        recovery.write(self.root, previous=self.previous, candidate=self.candidate)
        self.assertEqual(recovery.read(self.root)["previous"], self.previous)
        self.assertEqual((self.app / recovery.MARKER).stat().st_mode & 0o777, 0o600)
        recovery.clear(self.root)
        self.assertFalse((self.app / recovery.MARKER).exists())

    def test_existing_marker_not_overwritten(self):
        recovery.write(self.root, previous=self.previous, candidate=self.candidate)
        with self.assertRaises(RuntimeError):
            recovery.write(self.root, previous=self.candidate, candidate=self.previous)
        self.assertEqual(recovery.read(self.root)["previous"], self.previous)

    def test_symlink_marker_rejected(self):
        target = self.root / "other.json"
        target.write_text("{}")
        (self.app / recovery.MARKER).symlink_to(target)
        with self.assertRaises(OSError):
            recovery.read(self.root)

    def test_invalid_marker_is_not_removed(self):
        marker = self.app / recovery.MARKER
        marker.write_text(json.dumps({"version": 1, "previous": "../bad", "candidate": self.candidate}))
        marker.chmod(0o600)
        with self.assertRaises(ValueError):
            recovery.clear(self.root)
        self.assertTrue(marker.exists())

    def test_recover_previous_validated_release(self):
        old = atomic.install_release(self.app, {"__main__.py": b"old\n"})
        new = atomic.install_release(self.app, {"__main__.py": b"new\n"})
        recovery.write(self.root, previous=old, candidate=new)
        with atomic.install_lock(self.app):
            restored = recovery.recover(self.root, atomic)
        self.assertEqual(restored, old)
        self.assertEqual(os.readlink(self.app / "agent"), f"releases/{old}/agent")
        self.assertFalse((self.app / recovery.MARKER).exists())

    def test_recovery_failure_keeps_marker(self):
        new = atomic.install_release(self.app, {"__main__.py": b"new\n"})
        recovery.write(self.root, previous=self.previous, candidate=new)
        with atomic.install_lock(self.app):
            with self.assertRaises((OSError, RuntimeError)):
                recovery.recover(self.root, atomic)
        self.assertTrue((self.app / recovery.MARKER).exists())
