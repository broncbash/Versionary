"""Operator recovery command tests; no production filesystem access."""
import importlib.util
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


cli = load("recover-isolated-release.py", "test_recovery_cli")
journal = load("release-recovery.py", "test_recovery_cli_journal")
atomic = load("atomic-release.py", "test_recovery_cli_atomic")


class RecoveryCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)
        self.old = atomic.install_release(self.app, {"__main__.py": b"old\n"})
        self.new = atomic.install_release(self.app, {"__main__.py": b"new\n"})
        journal.write(self.root, previous=self.old, candidate=self.new)

    def test_inspect_does_not_modify(self):
        before = os.readlink(self.app / "agent")
        result = cli.inspect(root=self.root)
        self.assertEqual(result["status"], "recovery-pending")
        self.assertFalse(result["changes_made"])
        self.assertEqual(os.readlink(self.app / "agent"), before)
        self.assertTrue((self.app / journal.MARKER).exists())

    def test_explicit_recovery_restores_and_clears(self):
        result = cli.inspect(root=self.root, recover=True)
        self.assertEqual(result["status"], "restored")
        self.assertEqual(os.readlink(self.app / "agent"), f"releases/{self.old}/agent")
        self.assertFalse((self.app / journal.MARKER).exists())

    def test_unexpected_active_release_refuses_recovery(self):
        third = atomic.install_release(self.app, {"__main__.py": b"third\n"})
        with self.assertRaises(RuntimeError):
            cli.inspect(root=self.root, recover=True)
        self.assertEqual(os.readlink(self.app / "agent"), f"releases/{third}/agent")
        self.assertTrue((self.app / journal.MARKER).exists())

    def test_missing_marker_fails_closed(self):
        journal.clear(self.root)
        with self.assertRaises(FileNotFoundError):
            cli.inspect(root=self.root, recover=True)

    def test_rejects_production_root(self):
        with self.assertRaises(ValueError):
            cli.inspect(root="/", recover=True)
