"""Real loopback TLS acceptance for the operator-facing agent CLI.

Reuses the existing disposable HTTPS server fixture; never contacts homelab hosts.
"""
from pathlib import Path
from unittest.mock import patch

import versionary_agent_cli as cli
from agent.heartbeat import HeartbeatError
from tests.test_versionary_https_beta_journey import HTTPSBetaJourneyTests


class HTTPSAgentCLIJourneyTests(HTTPSBetaJourneyTests):
    """Run the real CLI through the entire approved agent lifecycle."""

    def test_complete_agent_lifecycle_over_https(self):
        paths = cli.state_paths(self.root / "cli-agent-state")
        self.assertEqual(
            cli.main([
                "--state-dir", str(paths["root"]),
                "setup", "--server", self.server_url,
                "--ca-cert", str(self.ca),
            ]),
            0,
        )
        self.assertEqual(
            cli.main(["--state-dir", str(paths["root"]), "status"]), 0
        )

        # Use a disposable identity, not the desktop's real identity.
        with patch.object(cli, "socket") as fake_socket, \
             patch.object(cli, "detect_platform", return_value="arch"):
            fake_socket.gethostname.return_value = "versionary-cli-tls-test"
            self.assertEqual(
                cli.main(["--state-dir", str(paths["root"]), "register"]), 0
            )

        identity = cli.existing_identity(paths)
        agent_id = identity["agent_id"]

        # Enrollment cannot succeed until the administrator approves it.
        with patch("builtins.print"):
            self.assertEqual(
                cli.main(["--state-dir", str(paths["root"]), "enroll"]), 1
            )
        self.assertFalse(paths["credential"].exists())

        status, result = self.request(
            f"/api/v1/admin/agents/{agent_id}/approve",
            method="POST", admin=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "approved")

        self.assertEqual(
            cli.main(["--state-dir", str(paths["root"]), "enroll"]), 0
        )
        self.assertTrue(paths["credential"].exists())
        self.assertFalse(paths["journal"].exists())

        # An already-provisioned identity is not silently replaced.
        self.assertEqual(
            cli.main(["--state-dir", str(paths["root"]), "enroll"]), 0
        )
        self.assertEqual(
            cli.main(["--state-dir", str(paths["root"]), "heartbeat"]), 0
        )

        synthetic = {
            "status": "success",
            "packages": [{
                "name": "cli-disposable-package",
                "installed": "1.0",
                "available": "1.1",
            }],
            "error": None,
        }
        with patch.object(cli, "scan", return_value=synthetic):
            self.assertEqual(
                cli.main(["--state-dir", str(paths["root"]), "report"]), 0
            )

        status, inventory = self.request("/api/v1/admin/agents", admin=True)
        self.assertEqual(status, 200)
        matching = [item for item in inventory["agents"] if item["id"] == agent_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["updates"], 1)
        self.assertEqual(matching[0]["scan_status"], "success")

        status, result = self.request(
            f"/api/v1/admin/agents/{agent_id}/revoke",
            method="POST", admin=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "revoked")

        # Revocation must be enforced by the server, not by CLI display logic.
        with patch("builtins.print"):
            self.assertEqual(
                cli.main(["--state-dir", str(paths["root"]), "heartbeat"]), 1
            )
        with patch.object(cli, "scan", return_value=synthetic), \
             patch("builtins.print"):
            self.assertEqual(
                cli.main(["--state-dir", str(paths["root"]), "report"]), 1
            )


if __name__ == "__main__":
    import unittest
    unittest.main()
