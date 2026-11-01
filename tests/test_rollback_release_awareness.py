"""Regression coverage for release-aware, read-only rollback planning."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "installer"
SPEC = importlib.util.spec_from_file_location(
    "versionary_release_aware_rollback",
    HERE / "rollback-plan.py",
)
rollback = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rollback)


class ReleaseAwareRollbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name) / "root"
        self.root.mkdir(mode=0o700)

        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.releases = self.app / "releases"
        self.releases.mkdir()

        self.identifier = "a" * 64
        (self.releases / self.identifier / "agent").mkdir(parents=True)

        self.snapshot = Path(temporary.name) / "snapshot"
        self.snapshot.mkdir(mode=0o700)

    def make_plan(self):
        fake_inventory = {
            "assets": {
                "etc/versionary-agent/config.json": {"present": False},
            },
            "private_state": "absent",
        }

        class Inventory:
            FILES = ("etc/versionary-agent/config.json",)

            @staticmethod
            def inspect(root):
                return fake_inventory

        class Snapshots:
            @staticmethod
            def verify(snapshot):
                return {"status": "verified"}

        class Manifest:
            @staticmethod
            def read_bytes():
                return (
                    b'{"version":1,"assets":'
                    b'{"etc/versionary-agent/config.json":{"present":false}}}'
                )

        original_load = rollback._load

        def load(filename, alias):
            if filename == "installation-inventory.py":
                return Inventory
            if filename == "installation-snapshot.py":
                return Snapshots
            return original_load(filename, alias)

        original_read_bytes = Path.read_bytes

        def read_bytes(path):
            if path == self.snapshot / "manifest.json":
                return Manifest.read_bytes()
            return original_read_bytes(path)

        with (
            patch.object(rollback, "_load", side_effect=load),
            patch.object(Path, "read_bytes", read_bytes),
        ):
            return rollback.plan(self.root, self.snapshot)

    def test_valid_release_is_reported_without_authorizing_rollback(self):
        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )

        result = self.make_plan()

        self.assertEqual(result["active_release"], self.identifier)
        self.assertTrue(result["active_release_present"])
        self.assertFalse(result["active_release_integrity_verified"])
        self.assertFalse(result["release_rollback_planned"])
        self.assertFalse(result["apply_allowed"])
        self.assertFalse(result["changes_made"])

    def test_missing_release_is_reported(self):
        result = self.make_plan()

        self.assertIsNone(result["active_release"])
        self.assertFalse(result["active_release_present"])
        self.assertFalse(result["apply_allowed"])

    def test_unsafe_release_pointer_blocks_plan(self):
        (self.app / "agent").symlink_to("/etc")

        with self.assertRaises(ValueError):
            self.make_plan()

    def test_no_rollback_execution(self):
        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )

        before = (self.app / "agent").readlink()
        result = self.make_plan()

        self.assertEqual((self.app / "agent").readlink(), before)
        self.assertFalse(result["systemd_started"])
        self.assertFalse(result["production_installed"])
        self.assertFalse(result["agent_enrolled"])


if __name__ == "__main__":
    unittest.main()
