"""Isolated snapshot creation and integrity regression checks."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

file = Path(__file__).resolve().parents[1] / "installer/installation-snapshot.py"
spec = importlib.util.spec_from_file_location("installation_snapshot", file)
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "root"
        self.root.mkdir(mode=0o700)
        self.output = base / "snapshot"
        self.config = self.root / "etc/versionary-agent/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"server":"https://example.test"}')

    def test_create_and_verify(self):
        result = snapshot.snapshot(self.root, self.output)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["asset_count"], 1)
        self.assertFalse(result["private_state_copied"])
        self.assertEqual(snapshot.verify(self.output)["status"], "verified")

    def test_tampered_payload_detected(self):
        snapshot.snapshot(self.root, self.output)
        (self.output / "asset-0").write_text("tampered")
        with self.assertRaises(ValueError):
            snapshot.verify(self.output)

    def test_existing_destination_not_overwritten(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            snapshot.snapshot(self.root, self.output)

    def test_rejects_live_root(self):
        with self.assertRaises(ValueError):
            snapshot.snapshot("/", self.output)

    def test_rejects_symlinked_source(self):
        self.config.unlink()
        self.config.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):
            snapshot.snapshot(self.root, self.output)

    def test_unexpected_snapshot_file_detected(self):
        snapshot.snapshot(self.root, self.output)
        (self.output / "extra").write_text("unexpected")
        with self.assertRaises(ValueError):
            snapshot.verify(self.output)

    def test_private_state_not_copied(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True, mode=0o700)
        (state / "token").write_text("private-token")
        snapshot.snapshot(self.root, self.output)
        self.assertFalse(any(b"private-token" in p.read_bytes() for p in self.output.iterdir()))
