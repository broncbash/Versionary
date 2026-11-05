"""Integration tests for the VERSIONARY AGENT CLI."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from agent.__main__ import main
from agent.credentials import CredentialError


IDENTITY = {
    "agent_id": "00000000-0000-4000-8000-000000000001",
    "hostname": "monitoring",
    "platform": "arch",
}

REPORT = {
    "status": "success",
    "packages": [],
    "error": None,
}


class TestAgentCLI(unittest.TestCase):

    def run_cli(self, command):
        output = io.StringIO()
        errors = io.StringIO()

        with (
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            code = main([command])

        return code, output.getvalue(), errors.getvalue()

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    def test_status_without_credential(self, platform, identity):
        platform.return_value = "arch"
        identity.return_value = IDENTITY

        with patch(
            "agent.__main__.load_credential",
            side_effect=CredentialError("Not provisioned"),
        ):
            code, output, _ = self.run_cli("status")

        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(output)["credential"],
            "not provisioned",
        )

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    @patch("agent.__main__.register_agent")
    def test_register(self, register, platform, identity):
        platform.return_value = "arch"
        identity.return_value = IDENTITY
        register.return_value = {"status": "pending"}

        code, output, _ = self.run_cli("register")

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "pending")
        register.assert_called_once_with(IDENTITY)

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    @patch("agent.__main__.load_credential")
    @patch("agent.__main__.send_heartbeat")
    def test_heartbeat(
        self, heartbeat, credential, platform, identity
    ):
        platform.return_value = "arch"
        identity.return_value = IDENTITY
        credential.return_value = "test-token"
        heartbeat.return_value = {"status": "ok"}

        code, output, _ = self.run_cli("heartbeat")

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "ok")
        heartbeat.assert_called_once_with(
            IDENTITY, "test-token"
        )

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    @patch("agent.__main__.load_credential")
    @patch("agent.__main__.scan")
    @patch("agent.__main__.send_report")
    def test_report(
        self, reporting, scan, credential, platform, identity
    ):
        platform.return_value = "arch"
        identity.return_value = IDENTITY
        credential.return_value = "test-token"
        scan.return_value = REPORT
        reporting.return_value = {"status": "recorded"}

        code, output, _ = self.run_cli("report")

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "recorded")
        reporting.assert_called_once_with(
            IDENTITY, "test-token", REPORT
        )

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    @patch("agent.__main__.load_credential")
    @patch("agent.__main__.send_heartbeat")
    def test_heartbeat_failure(
        self, heartbeat, credential, platform, identity
    ):
        platform.return_value = "arch"
        identity.return_value = IDENTITY
        credential.return_value = "test-token"
        heartbeat.side_effect = RuntimeError(
            "Agent reporting is disabled"
        )

        code, _, errors = self.run_cli("heartbeat")

        self.assertEqual(code, 1)
        self.assertIn(
            "Agent reporting is disabled",
            errors,
        )

    @patch("agent.__main__.get_or_create_identity")
    def test_scan_does_not_create_identity(self, identity):
        with patch(
            "agent.__main__.scan",
            return_value=REPORT,
        ):
            code, output, _ = self.run_cli("scan")

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["status"], "success")
        identity.assert_not_called()

    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform")
    @patch("agent.__main__.load_credential")
    @patch("agent.__main__.send_report")
    def test_missing_credential_prevents_report(
        self, reporting, credential, platform, identity
    ):
        platform.return_value = "arch"
        identity.return_value = IDENTITY
        credential.side_effect = RuntimeError(
            "Credential unavailable"
        )

        code, _, errors = self.run_cli("report")

        self.assertEqual(code, 1)
        self.assertIn("Credential unavailable", errors)
        reporting.assert_not_called()


if __name__ == "__main__":
    unittest.main()
