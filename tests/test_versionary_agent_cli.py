"""Offline tests for the opt-in Versionary agent CLI."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import versionary_agent_cli as cli


class AgentCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "state"
        self.ca = Path(self.temp.name) / "ca.crt"
        self.ca.write_text("test certificate placeholder", encoding="utf-8")
        self.paths = cli.state_paths(self.root)

    def test_setup_is_private_and_non_destructive(self):
        cli.setup(self.paths, "https://127.0.0.1:8766", str(self.ca))
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.paths["config"].stat().st_mode), 0o600)
        self.assertEqual(cli.read_config(self.paths)[0], "https://127.0.0.1:8766")
        with self.assertRaises(FileExistsError):
            cli.setup(self.paths, "https://127.0.0.1:8766", str(self.ca))

    def test_setup_rejects_http(self):
        with self.assertRaises(RuntimeError):
            cli.setup(self.paths, "http://127.0.0.1:8766", str(self.ca))
        self.assertFalse(self.root.exists())

    def test_setup_rejects_symlink_ca(self):
        link = Path(self.temp.name) / "link.crt"
        link.symlink_to(self.ca)
        with self.assertRaises(RuntimeError):
            cli.setup(self.paths, "https://127.0.0.1:8766", str(link))

    def test_status_never_prints_credential(self):
        cli.setup(self.paths, "https://127.0.0.1:8766", str(self.ca))
        with patch("builtins.print") as output:
            self.assertEqual(cli.run(type("Args", (), {
                "command": "status", "state_dir": str(self.root)
            })()), 0)
        text = " ".join(str(call) for call in output.call_args_list)
        self.assertIn("not registered", text)
        self.assertNotIn("Bearer ", text)

    def test_register_reuses_existing_protocol(self):
        cli.setup(self.paths, "https://127.0.0.1:8766", str(self.ca))
        args = type("Args", (), {"command": "register", "state_dir": str(self.root)})()
        identity = {"agent_id": "00000000-0000-4000-8000-000000000001",
                    "hostname": "offline-test", "platform": "arch"}
        with patch.object(cli, "identity_for", return_value=identity), \
             patch.object(cli, "register_v2", return_value={"status": "pending"}) as register:
            self.assertEqual(cli.run(args), 0)
        self.assertEqual(register.call_args.args[0], identity)
        self.assertEqual(register.call_args.kwargs["key_path"], self.paths["key"])

    def test_no_background_service_command(self):
        with self.assertRaises(SystemExit) as caught:
            cli.main(["install"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
