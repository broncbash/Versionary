"""Real disposable installer subprocess failure-injection tests."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"

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


trial = load(
    "disposable-install-trial.py",
    "real_failure_trial",
)

staging = load(
    "stage-beta.py",
    "real_failure_staging",
)


class RealSubprocessFailureMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(
            prefix="patch-command-fixtures-"
        )
        cls.addClassCleanup(cls.fixtures.cleanup)
        cls.fixture_root = Path(cls.fixtures.name)
        cls.certs = cls.fixture_root / "certs"
        cls.certs.mkdir(mode=0o700)

        subprocess.run(
            [
                sys.executable,
                str(INSTALLER / "generate-certificates.py"),
                "--hostname",
                "patch.example.test",
                "--output",
                str(cls.certs),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        cls.ca_cert = cls.certs / "ca.crt"
        cls.package = (
            INSTALLER / "dist/versionary-agent.tar.gz"
        )

        if not cls.ca_cert.is_file():
            raise RuntimeError("CA fixture generation failed")

        if not cls.package.is_file():
            raise RuntimeError("Agent package missing")

    def run_trial(self, fail_phase=None):
        observed_roots = []
        invoked_phases = []

        original_tempdir = tempfile.TemporaryDirectory
        original_run = subprocess.run

        class TrackedDirectory:
            def __init__(self, *args, **kwargs):
                self.context = original_tempdir(
                    *args, **kwargs
                )

            def __enter__(self):
                path = Path(self.context.__enter__())
                observed_roots.append(path)
                return str(path)

            def __exit__(self, *args):
                return self.context.__exit__(*args)

        def intercept(command, *args, **kwargs):
            if (
                isinstance(command, (list, tuple))
                and len(command) > 1
            ):
                phase = Path(str(command[1])).name

                if phase in PHASES:
                    invoked_phases.append(phase)

                    if phase == fail_phase:
                        raise subprocess.CalledProcessError(
                            97, command
                        )

            return original_run(
                command, *args, **kwargs
            )

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
            patch.object(
                trial,
                "load",
                return_value=staging,
            ),
        ):
            if fail_phase is None:
                result = trial.trial(
                    server="https://patch.example.test",
                    ca_cert=str(self.ca_cert),
                    package=self.package,
                )
                self.assertEqual(
                    result["status"], "passed"
                )
            else:
                with self.assertRaises(
                    subprocess.CalledProcessError
                ):
                    trial.trial(
                        server="https://patch.example.test",
                        ca_cert=str(self.ca_cert),
                        package=self.package,
                    )

        self.assertEqual(len(observed_roots), 1)

        self.assertFalse(
            observed_roots[0].exists(),
            "Disposable installation workspace survived",
        )

        return invoked_phases

    def test_successful_real_staging(self):
        phases = self.run_trial()
        self.assertEqual(
            phases[:len(PHASES)],
            list(PHASES),
        )

    def test_each_subprocess_failure(self):
        for phase in PHASES:
            with self.subTest(phase=phase):
                invoked = self.run_trial(
                    fail_phase=phase
                )
                self.assertIn(phase, invoked)

    def test_no_production_root_argument(self):
        self.assertNotIn(
            "--root",
            sys.argv,
        )


if __name__ == "__main__":
    unittest.main()
