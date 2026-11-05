"""Security regression tests for the Versionary agent CLI."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import versionary_agent_cli as cli


class AgentCLIHardeningTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.paths = cli.state_paths(self.root / "agent")

        self.ca = self.root / "ca.crt"
        self.ca.write_text("disposable-test-ca")

        cli.setup(
            self.paths,
            "https://127.0.0.1:8766",
            str(self.ca),
        )

    def test_rejects_identity_symlink(self):
        target = self.root / "identity-target.json"
        target.write_text("{}")

        self.paths["identity"].symlink_to(target)

        with self.assertRaises(RuntimeError):
            cli.existing_identity(self.paths)

    def test_rejects_world_readable_identity(self):
        identity = self.paths["identity"]

        identity.write_text(json.dumps({
            "agent_id": "00000000-0000-4000-8000-000000000001",
            "hostname": "test",
            "platform": "arch",
        }))

        identity.chmod(0o644)

        with self.assertRaises(RuntimeError):
            cli.existing_identity(self.paths)

    def test_accepts_private_identity(self):
        identity = self.paths["identity"]

        identity.write_text(json.dumps({
            "agent_id": "00000000-0000-4000-8000-000000000001",
            "hostname": "test",
            "platform": "arch",
        }))

        identity.chmod(0o600)

        loaded = cli.existing_identity(self.paths)

        self.assertEqual(loaded["hostname"], "test")

    def test_rejects_ca_symlink_after_setup(self):
        replacement = self.root / "replacement-ca.crt"
        replacement.write_text("replacement")

        self.ca.unlink()
        self.ca.symlink_to(replacement)

        with self.assertRaises(RuntimeError):
            cli.read_config(self.paths)

    def test_rejects_configuration_symlink(self):
        config = self.paths["config"]

        target = self.root / "replacement-config.json"
        target.write_text(config.read_text())

        config.unlink()
        config.symlink_to(target)

        with self.assertRaises(RuntimeError):
            cli.read_config(self.paths)


if __name__ == "__main__":
    unittest.main()
