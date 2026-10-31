"""Post-write failure injection against real disposable installer phases."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"
PACKAGE = INSTALLER / "dist/versionary-agent.tar.gz"

PHASES = (
    "install-files.py",
    "install-ca.py",
    "setup-config.py",
    "install-systemd.py",
    "audit-test-install.py",
)


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


trial = load("disposable-install-trial.py", "partial_write_trial")
staging = load("stage-beta.py", "partial_write_staging")


class PartialWriteFailureMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(
            prefix="patch-command-partial-fixtures-"
        )
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.certs = Path(cls.fixture.name) / "certs"
        cls.certs.mkdir(mode=0o700)

        subprocess.run(
            [
                sys.executable,
                str(INSTALLER / "generate-certificates.py"),
                "--hostname", "patch.example.test",
                "--output", str(cls.certs),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        cls.ca = cls.certs / "ca.crt"

        if not cls.ca.is_file() or not PACKAGE.is_file():
            raise RuntimeError("Required disposable fixtures missing")

    def exercise(self, fail_after=None):
        workspaces = []
        completed = []
        original_tempdir = tempfile.TemporaryDirectory
        original_run = subprocess.run

        class TrackedDirectory:
            def __init__(self, *args, **kwargs):
                self.context = original_tempdir(*args, **kwargs)

            def __enter__(self):
                location = self.context.__enter__()
                workspaces.append(Path(location))
                return location

            def __exit__(self, *args):
                return self.context.__exit__(*args)

        def intercept(command, *args, **kwargs):
            phase = (
                Path(str(command[1])).name
                if isinstance(command, (list, tuple)) and len(command) > 1
                else None
            )

            result = original_run(command, *args, **kwargs)

            if phase in PHASES:
                completed.append(phase)

                if phase == fail_after:
                    raise subprocess.CalledProcessError(
                        97, command,
                        output="Injected failure after successful subprocess",
                    )

            return result

        with (
            patch.object(
                trial.tempfile,
                "TemporaryDirectory",
                TrackedDirectory,
            ),
            patch.object(
                staging.subprocess,
                "run",
                side_effect=intercept,
            ),
            patch.object(trial, "load", return_value=staging),
        ):
            if fail_after is None:
                result = trial.trial(
                    server="https://patch.example.test",
                    ca_cert=str(self.ca),
                    package=PACKAGE,
                )
                self.assertEqual(result["status"], "passed")
                self.assertTrue(result["temporary_workspace_cleaned"])
            else:
                with self.assertRaises(subprocess.CalledProcessError):
                    trial.trial(
                        server="https://patch.example.test",
                        ca_cert=str(self.ca),
                        package=PACKAGE,
                    )

        self.assertEqual(len(workspaces), 1)
        self.assertFalse(
            workspaces[0].exists(),
            "Disposable workspace survived completion or failure",
        )

        return completed

    def test_real_successful_install_and_audit(self):
        completed = self.exercise()
        self.assertEqual(completed, list(PHASES))

    def test_failure_after_each_successful_phase(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                completed = self.exercise(fail_after=phase)
                expected = list(PHASES[:PHASES.index(phase) + 1])
                self.assertEqual(completed, expected)

    def test_invalid_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((ValueError, OSError, RuntimeError)):
                staging.stage(
                    root=tmp,
                    server="https://patch.example.test",
                    ca_cert=str(Path(tmp) / "missing-ca.pem"),
                    package=PACKAGE,
                )


if __name__ == "__main__":
    unittest.main()
