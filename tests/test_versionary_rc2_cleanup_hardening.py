"""Regression tests for the real RC2 installer cleanup helper."""

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "installer/versionary-server-install.py"
)
SPEC = importlib.util.spec_from_file_location(
    "versionary_rc2_installer_under_test", SOURCE
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class RC2CleanupHardeningTests(unittest.TestCase):
    def test_disable_oserror_is_reported_without_raising(self):
        output = io.StringIO()
        with patch.object(
            installer.subprocess, "run",
            side_effect=OSError("simulated executable failure"),
        ), contextlib.redirect_stderr(output):
            installer.recovery_systemctl(
                "disable", "--now", installer.SERVICE
            )
        self.assertIn("RECOVERY_CLEANUP_ERROR=", output.getvalue())
        self.assertIn("simulated executable failure", output.getvalue())

    def test_reload_oserror_is_reported_without_raising(self):
        output = io.StringIO()
        with patch.object(
            installer.subprocess, "run",
            side_effect=OSError("simulated reload failure"),
        ), contextlib.redirect_stderr(output):
            installer.recovery_systemctl("daemon-reload")
        self.assertIn("simulated reload failure", output.getvalue())

    def test_nonzero_cleanup_exit_is_reported(self):
        output = io.StringIO()
        with patch.object(
            installer.subprocess, "run",
            return_value=subprocess.CompletedProcess(
                ["systemctl"], 7
            ),
        ), contextlib.redirect_stderr(output):
            installer.recovery_systemctl("daemon-reload")
        self.assertIn("exited 7", output.getvalue())

    def test_successful_cleanup_has_no_error(self):
        output = io.StringIO()
        with patch.object(
            installer.subprocess, "run",
            return_value=subprocess.CompletedProcess(
                ["systemctl"], 0
            ),
        ), contextlib.redirect_stderr(output):
            installer.recovery_systemctl("daemon-reload")
        self.assertEqual("", output.getvalue())

    def test_recovery_handler_uses_guarded_cleanup(self):
        source = SOURCE.read_text()
        self.assertIn(
            'recovery_systemctl("disable", "--now", SERVICE)',
            source,
        )
        self.assertIn(
            'recovery_systemctl("daemon-reload")',
            source,
        )
        self.assertIn("INSTALLATION-FAILED.txt", source)
        self.assertIn("RECOVERY_REQUIRED=YES", source)


if __name__ == "__main__":
    unittest.main()
