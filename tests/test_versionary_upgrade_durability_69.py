"""Durability ordering for isolated upgrade transactions."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    "versionary-agent-isolated-coordinator.py",
    "versionary_durability69_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_durability69_upgrade",
)


class DurabilityTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-durability69-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.old = {
            name: f"old:{name}".encode()
            for name in coordinator.MODES
        }
        self.new = {
            name: f"new:{name}".encode()
            for name in coordinator.MODES
        }

        coordinator.install_payloads_isolated(
            self.root, self.old
        )

    def test_parent_synced_before_replacement(self):
        events = []
        original_fsync = os.fsync
        original_replace = upgrade.replace_file

        def monitored_fsync(fd):
            info = os.fstat(fd)
            root_info = self.root.stat()

            if (
                info.st_dev == root_info.st_dev
                and info.st_ino == root_info.st_ino
            ):
                events.append("root_sync")

            return original_fsync(fd)

        def monitored_replace(*args, **kwargs):
            events.append("replace")
            return original_replace(*args, **kwargs)

        with (
            patch.object(
                upgrade.os,
                "fsync",
                side_effect=monitored_fsync,
            ),
            patch.object(
                upgrade,
                "replace_file",
                side_effect=monitored_replace,
            ),
        ):
            upgrade.apply(self.root, self.old, self.new)

        self.assertIn("root_sync", events)
        self.assertIn("replace", events)
        self.assertLess(
            events.index("root_sync"),
            events.index("replace"),
        )

    def test_parent_sync_failure_blocks_changes(self):
        original_fsync = os.fsync

        def failing_fsync(fd):
            info = os.fstat(fd)
            root_info = self.root.stat()

            if (
                info.st_dev == root_info.st_dev
                and info.st_ino == root_info.st_ino
            ):
                raise OSError("Simulated parent sync failure")

            return original_fsync(fd)

        with patch.object(
            upgrade.os,
            "fsync",
            side_effect=failing_fsync,
        ):
            with self.assertRaises(OSError):
                upgrade.apply(
                    self.root,
                    self.old,
                    self.new,
                )

        for name, content in self.old.items():
            self.assertEqual(
                (self.root / name).read_bytes(),
                content,
            )

        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "recovery_required",
        )

        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root,
                self.old,
                self.new,
            )


if __name__ == "__main__":
    unittest.main()
