"""Tests for explicitly invoked v2 agent CLI commands."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from agent.__main__ import main
from agent.credentials import CredentialError


IDENTITY = {
    "agent_id": "12345678-1234-4234-8234-123456789abc",
    "hostname": "test-agent",
    "platform": "arch",
}


class TestAgentCLIV2(unittest.TestCase):

    @patch("agent.__main__.register_v2")
    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform", return_value="arch")
    def test_register_v2(
        self, platform, identity, register
    ):
        identity.return_value = IDENTITY
        register.return_value = {
            "agent_id": IDENTITY["agent_id"],
            "status": "pending",
        }

        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = main(["register-v2"])

        self.assertEqual(result, 0)
        register.assert_called_once_with(IDENTITY)
        self.assertEqual(
            json.loads(output.getvalue())["status"],
            "pending",
        )

    @patch("agent.__main__.complete_v2")
    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform", return_value="arch")
    def test_enroll_v2(
        self, platform, identity, complete
    ):
        identity.return_value = IDENTITY
        complete.return_value = {
            "agent_id": IDENTITY["agent_id"],
            "status": "enrolled",
            "recovered": False,
        }

        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            result = main(["enroll-v2"])

        self.assertEqual(result, 0)
        complete.assert_called_once_with(IDENTITY)
        self.assertEqual(
            json.loads(output.getvalue())["status"],
            "enrolled",
        )

    @patch("agent.__main__.register_v2")
    @patch("agent.__main__.complete_v2")
    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform", return_value="arch")
    def test_status_does_not_trigger_enrollment(
        self, platform, identity, complete, register
    ):
        identity.return_value = IDENTITY

        with patch(
            "agent.__main__.load_credential",
            side_effect=CredentialError("not provisioned"),
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["status"])

        self.assertEqual(result, 0)
        register.assert_not_called()
        complete.assert_not_called()

    @patch("agent.__main__.register_agent")
    @patch("agent.__main__.get_or_create_identity")
    @patch("agent.__main__.detect_platform", return_value="arch")
    def test_original_register_remains_v1(
        self, platform, identity, register
    ):
        identity.return_value = IDENTITY
        register.return_value = {"status": "pending"}

        with contextlib.redirect_stdout(io.StringIO()):
            result = main(["register"])

        self.assertEqual(result, 0)
        register.assert_called_once_with(IDENTITY)


if __name__ == "__main__":
    unittest.main()
