"""Regression tests for isolated systemd unit installation."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/install-systemd.py"

SPEC = importlib.util.spec_from_file_location(
    "arby_systemd_installer_tests", SCRIPT
)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)

SERVICE = "arby-patch-agent.service"
TIMER = "arby-patch-agent.timer"


class SystemdInstallerTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.root = Path(self.temporary.name)
        self.destination = self.root / "etc/systemd/system"

    def test_initial_installation(self):
        INSTALLER.install_units(self.root)

        for name in (SERVICE, TIMER):
            path = self.destination / name

            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            self.assertEqual(
                path.stat().st_mode & 0o777,
                0o644,
            )

    def test_identical_reinstallation(self):
        INSTALLER.install_units(self.root)

        before = {
            name: (self.destination / name).read_bytes()
            for name in (SERVICE, TIMER)
        }

        INSTALLER.install_units(self.root)

        for name in (SERVICE, TIMER):
            self.assertEqual(
                (self.destination / name).read_bytes(),
                before[name],
            )

    def test_conflicting_timer_prevents_partial_install(self):
        self.destination.mkdir(parents=True)

        timer = self.destination / TIMER
        timer.write_text("CONFLICTING TIMER\n")

        with self.assertRaisesRegex(RuntimeError, "differs"):
            INSTALLER.install_units(self.root)

        self.assertFalse(
            (self.destination / SERVICE).exists()
        )
        self.assertEqual(
            timer.read_text(),
            "CONFLICTING TIMER\n",
        )

    def test_symlink_rejected(self):
        self.destination.mkdir(parents=True)

        service = self.destination / SERVICE
        service.symlink_to(self.destination / TIMER)

        with self.assertRaises((OSError, RuntimeError)):
            INSTALLER.install_units(self.root)

        self.assertTrue(service.is_symlink())

    def test_second_unit_failure_rolls_back_both(self):
        original_fsync = os.fsync
        calls = 0

        def fail_second(fd):
            nonlocal calls
            calls += 1

            if calls == 2:
                raise OSError("SIMULATED SECOND UNIT FAILURE")

            return original_fsync(fd)

        with patch.object(INSTALLER.os, "fsync", fail_second):
            with self.assertRaisesRegex(
                OSError, "SIMULATED"
            ):
                INSTALLER.install_units(self.root)

        self.assertFalse(
            (self.destination / SERVICE).exists()
        )
        self.assertFalse(
            (self.destination / TIMER).exists()
        )

        INSTALLER.install_units(self.root)

        self.assertTrue(
            (self.destination / SERVICE).is_file()
        )
        self.assertTrue(
            (self.destination / TIMER).is_file()
        )

    def test_failure_preserves_existing_service(self):
        INSTALLER.install_units(self.root)

        service = self.destination / SERVICE
        timer = self.destination / TIMER

        original_service = service.read_bytes()
        timer.unlink()

        original_fsync = os.fsync

        def fail_write(fd):
            raise OSError("SIMULATED TIMER FAILURE")

        with patch.object(INSTALLER.os, "fsync", fail_write):
            with self.assertRaisesRegex(
                OSError, "SIMULATED"
            ):
                INSTALLER.install_units(self.root)

        self.assertEqual(
            service.read_bytes(),
            original_service,
        )
        self.assertFalse(timer.exists())


if __name__ == "__main__":
    unittest.main()
