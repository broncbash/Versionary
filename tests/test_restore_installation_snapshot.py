"""Regression tests for empty-root-only snapshot restoration."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "installer"
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

restore = module("restore_snapshot_test", "restore-installation-snapshot.py")
snapshot = module("snapshot_for_restore_test", "installation-snapshot.py")

class RestoreSnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.source = base / "source"
        self.source.mkdir(mode=0o700)
        self.config = self.source / "etc/versionary-agent/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"server":"https://example.test"}')
        self.config.chmod(0o600)
        self.snap = base / "snapshot"
        snapshot.snapshot(self.source, self.snap)
        self.root = base / "restored"
        self.root.mkdir(mode=0o700)

    def test_restore_and_permissions(self):
        result = restore.restore(self.snap, self.root)
        target = self.root / "etc/versionary-agent/config.json"
        self.assertEqual(target.read_bytes(), self.config.read_bytes())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["production_installed"])
        self.assertFalse(result["private_state_restored"])

    def test_existing_asset_refused(self):
        (self.root / "marker").write_text("preserve")
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)
        self.assertEqual((self.root / "marker").read_text(), "preserve")

    def test_symlink_root_refused(self):
        self.root.rmdir()
        self.root.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)

    def test_tampered_snapshot_refused_without_writes(self):
        (self.snap / "asset-0").write_bytes(b"bad")
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_manifest_rejects_unsafe_mode_before_writes(self):
        manifest_path = self.snap / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["assets"]["etc/versionary-agent/config.json"]["mode"] = "0o666"
        manifest_path.write_text(json.dumps(manifest))
        manifest_path.chmod(0o600)
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_manifest_rejects_invalid_mode_before_writes(self):
        manifest_path = self.snap / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["assets"]["etc/versionary-agent/config.json"]["mode"] = "0o9"
        manifest_path.write_text(json.dumps(manifest))
        manifest_path.chmod(0o600)
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_manifest_rejects_unknown_fields(self):
        manifest_path = self.snap / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["unexpected"] = "injected"
        manifest_path.write_text(json.dumps(manifest))
        manifest_path.chmod(0o600)
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.root)

    def test_live_root_refused(self):
        with self.assertRaises(ValueError):
            restore.restore(self.snap, "/")

    def test_overlapping_root_refused(self):
        with self.assertRaises(ValueError):
            restore.restore(self.snap, self.snap)

    def test_partial_failure_preserves_artifacts(self):
        original = restore.os.open
        def fail_second(path, flags, *args, **kwargs):
            if str(path).endswith("ca.crt") and flags & os.O_CREAT:
                raise OSError("injected interruption")
            return original(path, flags, *args, **kwargs)
        ca = self.source / "etc/versionary-agent/ca.crt"
        ca.write_text("public-ca")
        snapshot_dir = self.snap.parent / "second-snapshot"
        snapshot.snapshot(self.source, snapshot_dir)
        with patch.object(restore.os, "open", side_effect=fail_second):
            with self.assertRaises(OSError):
                restore.restore(snapshot_dir, self.root)
        self.assertTrue((self.root / "etc/versionary-agent/config.json").exists())
        with self.assertRaises(ValueError):
            restore.restore(snapshot_dir, self.root)

if __name__ == "__main__":
    unittest.main()
