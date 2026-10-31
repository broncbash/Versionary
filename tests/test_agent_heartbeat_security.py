"""Security regression tests for VERSIONARY AGENT heartbeat."""


import io
import json
import unittest
from unittest.mock import patch

from agent.heartbeat import HeartbeatError, send_heartbeat


IDENTITY = {
    "agent_id": "00000000-0000-4000-8000-000000000001",
    "hostname": "monitoring",
    "platform": "arch",
}


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(payload)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestHeartbeatSecurity(unittest.TestCase):
    def setUp(self):
        self._config_patch = unittest.mock.patch("agent.config.load_config", return_value={"server": "https://example.test", "ca_cert": "/tmp/arby-test-ca.crt"})
        self._config_patch.start()
        self.addCleanup(self._config_patch.stop)


    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_empty_token(self, builder):
        with self.assertRaises(HeartbeatError):
            send_heartbeat(IDENTITY, "")

        builder.assert_not_called()

    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_token_with_newline(self, builder):
        with self.assertRaises(HeartbeatError):
            send_heartbeat(IDENTITY, "secret\ninjection")

        builder.assert_not_called()

    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_invalid_uuid(self, builder):
        identity = dict(IDENTITY)
        identity["agent_id"] = "../invalid"

        with self.assertRaises(HeartbeatError):
            send_heartbeat(identity, "test-token")

        builder.assert_not_called()

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_unexpected_status(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            b'{"status":"ok"}',
            status=202,
        )

        with self.assertRaisesRegex(
            HeartbeatError, "Unexpected heartbeat HTTP status"
        ):
            send_heartbeat(IDENTITY, "test-token")

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_oversized_response(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(b"x" * 8193)

        with self.assertRaisesRegex(
            HeartbeatError, "too large"
        ):
            send_heartbeat(IDENTITY, "test-token")

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_invalid_json(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(b"{invalid")

        with self.assertRaisesRegex(
            HeartbeatError, "Invalid heartbeat response"
        ):
            send_heartbeat(IDENTITY, "test-token")

    @patch("agent.heartbeat.ssl.create_default_context")
    @patch("agent.heartbeat.urllib.request.build_opener")
    def test_reject_non_object_response(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            json.dumps(["unexpected"]).encode()
        )

        with self.assertRaisesRegex(
            HeartbeatError, "Invalid heartbeat response"
        ):
            send_heartbeat(IDENTITY, "test-token")


if __name__ == "__main__":
    unittest.main()
