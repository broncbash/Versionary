"""Recovery after a simulated post-replacement sync failure."""

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
    "versionary_sync70_coordinator",
)
upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_sync70_upgrade",
)


class SyncFailureTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-sync70-"
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

    def test_failed_replacement_sync_retains_recovery(self):
        original_fsync = os.fsync
        target_parent = (
            self.root / sorted(self.old)[0]
        ).parent

        failed = False

        def injected_fsync(fd):
            nonlocal failed

            info = os.fstat(fd)
            parent = target_parent.stat()

            if (
                not failed
                and info.st_dev == parent.st_dev
                and info.st_ino == parent.st_ino
            ):
                failed = True
                raise OSError(
                    "Simulated post-replacement sync failure"
                )

            return original_fsync(fd)

        with patch.object(
            upgrade.os,
            "fsync",
            side_effect=injected_fsync,
        ):
            with self.assertRaises(OSError):
                upgrade.apply(
                    self.root,
                    self.old,
                    self.new,
                )

        self.assertTrue(failed)

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

        result = upgrade.recover_to_old(self.root)

        self.assertEqual(result["restored"], 1)

        self.assertEqual(
            upgrade.review_complete(self.root)["status"],
            "original_restored",
        )

        for name, expected in self.old.items():
            self.assertEqual(
                (self.root / name).read_bytes(),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
