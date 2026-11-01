"""Read-only rollback integration tests for release integrity."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "installer"


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = load("rollback-plan.py", "versionary_integrity_rollback_planner")
atomic = load("atomic-release.py", "versionary_integrity_rollback_atomic")


class RollbackIntegrityIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name) / "root"
        self.root.mkdir(mode=0o700)

        self.snapshot = Path(temporary.name) / "snapshot"
        self.snapshot.mkdir(mode=0o700)

        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.modules = {
            "__main__.py": b"print('versionary')\n",
        }

        self.identifier = atomic.release_id(self.modules)
        self.release = (
            self.app / "releases" / self.identifier / "agent"
        )
        self.release.mkdir(parents=True)

        for name, data in self.modules.items():
            (self.release / name).write_bytes(data)

        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )

    def plan(self):
        class Inventory:
            FILES = ("etc/versionary-agent/config.json",)

            @staticmethod
            def inspect(root):
                return {
                    "assets": {
                        "etc/versionary-agent/config.json": {
                            "present": False,
                        },
                    },
                    "private_state": "absent",
                }

        class Snapshots:
            @staticmethod
            def verify(snapshot):
                return True

        original_load = planner._load

        def module_loader(filename, alias):
            if filename == "installation-inventory.py":
                return Inventory
            if filename == "installation-snapshot.py":
                return Snapshots
            return original_load(filename, alias)

        original_read_bytes = Path.read_bytes

        def read_bytes(path):
            if path == self.snapshot / "manifest.json":
                return (
                    b'{"version":1,"assets":'
                    b'{"etc/versionary-agent/config.json":{"present":false}}}'
                )
            return original_read_bytes(path)

        with (
            patch.object(planner, "_load", side_effect=module_loader),
            patch.object(Path, "read_bytes", read_bytes),
        ):
            return planner.plan(self.root, self.snapshot)

    def test_valid_release_integrity_reported(self):
        result = self.plan()
        self.assertTrue(result["active_release_integrity_verified"])
        self.assertEqual(
            result["active_release_integrity_status"],
            "verified",
        )
        self.assertFalse(result["active_release_authenticity_verified"])
        self.assertFalse(result["active_release_provenance_verified"])
        self.assertFalse(result["apply_allowed"])
        self.assertFalse(result["release_rollback_planned"])

    def test_tampered_release_refuses_plan(self):
        (self.release / "__main__.py").write_bytes(b"tampered\n")
        with self.assertRaises(ValueError):
            self.plan()

    def test_no_active_release_remains_supported(self):
        (self.app / "agent").unlink()
        result = self.plan()
        self.assertFalse(result["active_release_integrity_verified"])
        self.assertEqual(
            result["active_release_integrity_status"],
            "absent",
        )


if __name__ == "__main__":
    unittest.main()
