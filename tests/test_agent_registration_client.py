"""Tests for the standalone agent registration client."""


import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from agent.registration import (
    RegistrationError,
    register_agent,
)


IDENTITY = {
    "agent_id": "00000000-0000-4000-8000-000000000001",
    "hostname": "monitoring",
    "platform": "arch",
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestAgentRegistrationClient(unittest.TestCase):
    def setUp(self):
        self._config_patch = unittest.mock.patch("agent.config.load_config", return_value={"server": "https://example.test", "ca_cert": "/tmp/arby-test-ca.crt"})
        self._config_patch.start()
        self.addCleanup(self._config_patch.stop)


    @patch("agent.registration.ssl.create_default_context")
    @patch("agent.registration.urllib.request.urlopen")
    def test_success(self, urlopen, context):
        urlopen.return_value = FakeResponse(
            json.dumps({
                "agent_id": IDENTITY["agent_id"],
                "status": "pending",
            }).encode()
        )

        result = register_agent(IDENTITY)

        self.assertEqual(result["status"], "pending")
        self.assertEqual(
            urlopen.call_args.kwargs["timeout"],
            15,
        )
        context.assert_called_once()

    def test_reject_http(self):
        with self.assertRaises(RegistrationError):
            register_agent(
                IDENTITY,
                server="http://192.168.86.15",
            )

    @patch("agent.registration.ssl.create_default_context")
    @patch("agent.registration.urllib.request.urlopen")
    def test_registration_disabled(self, urlopen, _context):
        error = urllib.error.HTTPError(
            "https://example.test",
            503,
            "Unavailable",
            {},
            None,
        )
        self.addCleanup(error.close)
        urlopen.side_effect = error

        with self.assertRaisesRegex(
            RegistrationError, "disabled"
        ):
            register_agent(IDENTITY)

    @patch("agent.registration.ssl.create_default_context")
    @patch("agent.registration.urllib.request.urlopen")
    def test_duplicate_registration(self, urlopen, _context):
        error = urllib.error.HTTPError(
            "https://example.test",
            409,
            "Conflict",
            {},
            None,
        )
        self.addCleanup(error.close)
        urlopen.side_effect = error

        with self.assertRaisesRegex(
            RegistrationError, "already registered"
        ):
            register_agent(IDENTITY)

    @patch("agent.registration.ssl.create_default_context")
    @patch("agent.registration.urllib.request.urlopen")
    def test_identity_mismatch(self, urlopen, _context):
        urlopen.return_value = FakeResponse(
            json.dumps({
                "agent_id": "different",
                "status": "pending",
            }).encode()
        )

        with self.assertRaisesRegex(
            RegistrationError, "unexpected agent identity"
        ):
            register_agent(IDENTITY)


if __name__ == "__main__":
    unittest.main()
