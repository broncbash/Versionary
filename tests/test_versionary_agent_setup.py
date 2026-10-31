"""Offline tests for portable Versionary agent setup."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from versionary_agent_cli import read_config, state_paths


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/versionary-agent-setup.py"

spec = importlib.util.spec_from_file_location(
    "versionary_portable_setup", INSTALLER
)
setup_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_module)


class PortableSetupTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.state = self.root / "agent-state"
        self.ca = self.root / "ca.crt"
        self.ca.write_text("disposable test CA")

    def args(self, *extra):
        return [
            "--server", "https://127.0.0.1:8766",
            "--ca-cert", str(self.ca),
            "--state-dir", str(self.state),
            *extra,
        ]

    def test_dry_run_creates_nothing(self):
        self.assertEqual(
            setup_module.run(self.args("--dry-run")), 0
        )
        self.assertFalse(self.state.exists())

    def test_setup_creates_private_config(self):
        self.assertEqual(setup_module.run(self.args()), 0)

        paths = state_paths(self.state)

        self.assertEqual(
            stat.S_IMODE(self.state.stat().st_mode), 0o700
        )
        self.assertEqual(
            stat.S_IMODE(paths["config"].stat().st_mode), 0o600
        )
        self.assertEqual(
            read_config(paths)[0],
            "https://127.0.0.1:8766",
        )

    def test_refuses_overwrite(self):
        self.assertEqual(setup_module.run(self.args()), 0)

        original = (
            self.state / "config.json"
        ).read_bytes()

        self.assertEqual(setup_module.run(self.args()), 1)

        self.assertEqual(
            (self.state / "config.json").read_bytes(),
            original,
        )

    def test_rejects_http(self):
        args = self.args()
        args[1] = "http://127.0.0.1:8766"

        self.assertEqual(setup_module.run(args), 1)
        self.assertFalse(self.state.exists())

    def test_rejects_ca_symlink(self):
        link = self.root / "ca-link.crt"
        link.symlink_to(self.ca)

        args = self.args()
        args[3] = str(link)

        self.assertEqual(setup_module.run(args), 1)
        self.assertFalse(self.state.exists())

    def test_rejects_missing_ca(self):
        args = self.args()
        args[3] = str(self.root / "missing.crt")

        self.assertEqual(setup_module.run(args), 1)
        self.assertFalse(self.state.exists())

    def test_requires_explicit_connection_settings(self):
        self.assertEqual(
            setup_module.run([
                "--state-dir", str(self.state)
            ]),
            1,
        )
        self.assertFalse(self.state.exists())

    def test_interactive_requires_terminal(self):
        with patch.object(
            setup_module.sys.stdin, "isatty",
            return_value=False,
        ):
            self.assertEqual(
                setup_module.run([
                    "--interactive",
                    "--state-dir", str(self.state),
                ]),
                1,
            )

        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
