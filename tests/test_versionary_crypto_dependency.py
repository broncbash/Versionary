"""Friendly agent launcher dependency preflight regression tests."""

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/install-versionary-agent"


def load_launcher():
    from importlib.machinery import SourceFileLoader

    name = "versionary_crypto_preflight"
    loader = SourceFileLoader(name, str(SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)

    if spec is None:
        raise RuntimeError("Unable to load agent launcher")

    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class CryptoDependencyTests(unittest.TestCase):

    def setUp(self):
        self.launcher = load_launcher()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def run_launcher(self, *args, missing=True):
        stderr = io.StringIO()
        stdout = io.StringIO()

        argv = [
            str(SCRIPT),
            "--distribution",
            str(Path(self.temp.name) / "distribution.tar.gz"),
            "--server",
            "https://example.test",
            "--ca-cert",
            str(Path(self.temp.name) / "ca.crt"),
            *args,
        ]

        real_find_spec = importlib.util.find_spec

        def find_spec(name, *arguments):
            if name == "cryptography" and missing:
                return None
            return real_find_spec(name, *arguments)

        with (
            patch.object(sys, "argv", argv),
            patch.object(
                self.launcher.importlib.util,
                "find_spec",
                side_effect=find_spec,
            ),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(stdout),
        ):
            return self.launcher.main(), stderr.getvalue()

    def test_missing_dependency_has_clear_guidance(self):
        result, error = self.run_launcher("--dry-run")
        self.assertEqual(result, 1)
        self.assertIn("cryptography", error)
        self.assertIn("python3-cryptography", error)
        self.assertIn("python-cryptography", error)

    def test_disposable_execution_stops_before_install(self):
        with patch.object(
            self.launcher.subprocess,
            "run",
            side_effect=AssertionError("Installer executed"),
        ):
            result, error = self.run_launcher(
                "--execute-disposable",
                "--yes",
                "--root",
                self.temp.name,
            )
        self.assertEqual(result, 1)
        self.assertIn("Missing Python dependency", error)

    def test_planning_mode_does_not_require_dependency(self):
        result, error = self.run_launcher()
        self.assertEqual(result, 0)
        self.assertEqual(error, "")


if __name__ == "__main__":
    unittest.main()
