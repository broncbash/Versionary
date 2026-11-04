"""Regression tests for the installed Versionary agent runtime."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SERVICE = (
    ROOT
    / "installer"
    / "systemd"
    / "versionary-agent.service"
)

TIMER = (
    ROOT
    / "installer"
    / "systemd"
    / "versionary-agent.timer"
)

CLI = ROOT / "versionary_agent_cli.py"


class VersionarySystemdRuntimeTests(unittest.TestCase):

    def test_service_uses_system_aware_cli(self):
        text = SERVICE.read_text()

        self.assertIn(
            "ExecStart=/usr/bin/python3 "
            "/opt/versionary-agent/versionary_agent_cli.py "
            "--system report",
            text,
        )

        self.assertNotIn(
            "ExecStart=/usr/bin/python3 -m agent report",
            text,
        )

    def test_service_preserves_private_state(self):
        text = SERVICE.read_text()

        self.assertIn("User=root", text)
        self.assertIn(
            "ReadWritePaths=/var/lib/versionary-agent",
            text,
        )
        self.assertIn("UMask=0077", text)
        self.assertIn("ProtectSystem=strict", text)
        self.assertIn("NoNewPrivileges=yes", text)

    def test_timer_is_not_automatically_activated(self):
        text = TIMER.read_text()

        self.assertIn(
            "Unit=versionary-agent.service",
            text,
        )
        self.assertIn(
            "Persistent=false",
            text,
        )

    def test_cli_has_system_state_contract(self):
        text = CLI.read_text()

        self.assertIn(
            'SYSTEM_STATE = Path("/var/lib/versionary-agent")',
            text,
        )
        self.assertIn(
            'SYSTEM_CONFIG = Path("/etc/versionary-agent/config.json")',
            text,
        )
        self.assertIn('"--system"', text)
        self.assertIn("read_system_config(paths)", text)


if __name__ == "__main__":
    unittest.main()
