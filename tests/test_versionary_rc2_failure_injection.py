"""Isolated failure-injection tests for the RC2 installer."""

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-server-install.py"
SPEC = importlib.util.spec_from_file_location(
    "versionary_rc2_failure_injection", SOURCE
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)

REAL_PATH = Path


class RC2FailureInjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="versionary-rc2-failure-test-"
        )
        self.addCleanup(self.tmp.cleanup)
        self.base = REAL_PATH(self.tmp.name)
        self.app = self.base / "app"
        self.state = self.base / "state"
        self.unit_dir = self.base / "systemd"
        self.unit_dir.mkdir()
        self.archive = self.base / "release.tar.gz"

        with tarfile.open(self.archive, "w:gz") as archive:
            payload = self.base / "sample.txt"
            payload.write_text("isolated test")
            archive.add(payload, arcname="sample.txt")

        self.args = SimpleNamespace(
            archive=str(self.archive),
            app_dir=str(self.app),
            state_dir=str(self.state),
            confirm_disposable=True,
            tls_identity="127.0.0.1",
            bind_address="127.0.0.1",
            port=8766,
        )

    def mapped_path(self, value):
        if str(value) == "/etc/systemd/system":
            return self.unit_dir
        if str(value) == "/run/systemd/system":
            return self.unit_dir
        return REAL_PATH(value)

    def run_failure(self, failure_command, cleanup_error):
        output = io.StringIO()
        commands = []

        def fake_run(*command, **kwargs):
            commands.append(command)
            if command[0] == failure_command:
                raise RuntimeError("ORIGINAL_INSTALL_FAILURE")
            return None

        def fake_subprocess(command, **kwargs):
            raise OSError(cleanup_error)

        with (
            patch.object(installer, "Path", side_effect=self.mapped_path),
            patch.object(installer.os, "geteuid", return_value=0),
            patch.object(installer.pwd, "getpwall", return_value=[]),
            patch.object(installer.shutil, "which", return_value="/usr/bin/mock"),
            patch.object(installer, "run", side_effect=fake_run),
            patch.object(
                installer.subprocess,
                "run",
                side_effect=fake_subprocess,
            ),
            contextlib.redirect_stderr(output),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "ORIGINAL_INSTALL_FAILURE"
            ):
                installer.install(self.args, "test-digest")

        return output.getvalue(), commands

    def test_early_failure_preserves_original_exception(self):
        output, commands = self.run_failure(
            "useradd", "SIMULATED_RELOAD_FAILURE"
        )

        self.assertIn("INSTALL_FAILED=RECOVERY_REQUIRED", output)
        self.assertIn("RECOVERY_REQUIRED=YES", output)
        self.assertIn("SIMULATED_RELOAD_FAILURE", output)
        self.assertFalse(self.app.exists())
        self.assertFalse(self.state.exists())
        self.assertTrue(commands)

    def test_partial_install_preserves_state_and_marker(self):
        output, commands = self.run_failure(
            "chown", "SIMULATED_CLEANUP_FAILURE"
        )

        marker = self.state / "INSTALLATION-FAILED.txt"

        self.assertTrue(self.app.is_dir())
        self.assertTrue(self.state.is_dir())
        self.assertTrue(marker.is_file())
        self.assertIn(
            "preserved for inspection",
            marker.read_text(),
        )
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        self.assertIn("RECOVERY_REQUIRED=YES", output)
        self.assertIn("SIMULATED_CLEANUP_FAILURE", output)
        self.assertTrue(commands)


if __name__ == "__main__":
    unittest.main()
