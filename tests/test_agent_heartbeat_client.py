"""Tests for the ARBY PATCH AGENT heartbeat client."""


import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from agent.heartbeat import (
    HeartbeatError,
    send_heartbeat,
)


IDENTITY = {
    "agent_id": "00000000-0000-4000-8000-000000000001",
    "hostname": "monitoring",
    "platform": "arch",
}


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestHeartbeatClient(unittest.TestCase):
    def setUp(self):
        self._config_patch = unittest.mock.patch("agent.config.load_config", return_value={"server": "https://example.test", "ca_cert": "/tmp/arby-test-ca.crt"})
        self._config_patch.start()
        self.addCleanup(self._config_patch.stop)


    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_success(self, builder, context):
        builder.return_value.open.return_value = FakeResponse(
            json.dumps({
                "status": "ok",
            }).encode()
        )

        result = send_heartbeat(
            IDENTITY,
            "test-token",
        )

        self.assertEqual(result["status"], "ok")

        request = builder.return_value.open.call_args.args[0]

        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer test-token",
        )

        context.assert_called_once()

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_redirect_handler_never_forwards_bearer_token(self, builder, _context):
        import urllib.request
        redirect = urllib.error.HTTPError(
            "https://example.test", 307, "Temporary Redirect",
            {"Location": "https://attacker.example/steal"}, None)
        self.addCleanup(redirect.close)
        builder.return_value.open.side_effect = redirect
        with self.assertRaisesRegex(HeartbeatError, "HTTP 307"):
            send_heartbeat(IDENTITY, "test-token")
        handlers = builder.call_args.args
        redirect_handler = next(
            handler for handler in handlers
            if isinstance(handler, urllib.request.HTTPRedirectHandler))
        request = urllib.request.Request(
            "https://example.test/agent", data=b"{}",
            headers={"Authorization": "Bearer secret"}, method="POST")
        self.assertIsNone(redirect_handler.redirect_request(
            request, None, 307, "redirect",
            {"Location": "https://attacker.example/steal"},
            "https://attacker.example/steal"))

    def test_reject_http(self):
        with self.assertRaises(HeartbeatError):
            send_heartbeat(
                IDENTITY,
                "test-token",
                server="http://192.168.86.15",
            )

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_unauthorized(self, builder, _context):
        error = urllib.error.HTTPError(
            "https://example.test",
            401,
            "Unauthorized",
            {},
            None,
        )
        self.addCleanup(error.close)
        builder.return_value.open.side_effect = error

        with self.assertRaisesRegex(
            HeartbeatError, "authentication rejected"
        ):
            send_heartbeat(IDENTITY, "test-token")

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reporting_disabled(self, builder, _context):
        error = urllib.error.HTTPError(
            "https://example.test",
            503,
            "Unavailable",
            {},
            None,
        )
        self.addCleanup(error.close)
        builder.return_value.open.side_effect = error

        with self.assertRaisesRegex(
            HeartbeatError, "reporting is disabled"
        ):
            send_heartbeat(IDENTITY, "test-token")

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_invalid_response(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            json.dumps(["unexpected"]).encode()
        )

        with self.assertRaisesRegex(
            HeartbeatError, "Invalid heartbeat response"
        ):
            send_heartbeat(IDENTITY, "test-token")


if __name__ == "__main__":
    unittest.main()
