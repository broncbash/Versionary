"""Unit tests for enrollment HTTPS transport."""


import json
import unittest
from unittest.mock import patch, MagicMock

from agent.enrollment_http import (
    post_json,
    EnrollmentHTTPError,
)


class TestEnrollmentHTTP(unittest.TestCase):
    def setUp(self):
        self._config_patch = unittest.mock.patch("agent.config.load_config", return_value={"server": "https://example.test", "ca_cert": "/tmp/arby-test-ca.crt"})
        self._config_patch.start()
        self.addCleanup(self._config_patch.stop)


    def test_reject_http(self):
        with self.assertRaises(EnrollmentHTTPError):
            post_json(
                "/api/v2/agents/register",
                {},
                server="http://localhost",
            )

    def test_reject_credentials_in_url(self):
        with self.assertRaises(EnrollmentHTTPError):
            post_json(
                "/api/v2/agents/register",
                {},
                server="https://user:pass@example.com",
            )

    def test_reject_unexpected_path(self):
        with self.assertRaises(EnrollmentHTTPError):
            post_json("/api/v1/agents/register", {})

    def test_reject_server_path(self):
        with self.assertRaises(EnrollmentHTTPError):
            post_json(
                "/api/v2/agents/register",
                {},
                server="https://example.com/other",
            )

    @patch("agent.enrollment_http.urllib.request.build_opener")
    @patch("agent.enrollment_http.ssl.create_default_context")
    def test_success(self, mock_context, mock_builder):
        response = MagicMock()
        response.status = 201
        response.read.return_value = json.dumps({
            "agent_id": "test",
            "status": "pending",
        }).encode()

        mock_builder.return_value.open.return_value.__enter__.return_value = (
            response
        )

        result = post_json("/api/v2/agents/register", {})

        self.assertEqual(result["status"], "pending")
        mock_context.assert_called_once()

    @patch("agent.enrollment_http.urllib.request.build_opener")
    @patch("agent.enrollment_http.ssl.create_default_context")
    def test_reject_oversized_response(self, mock_context, mock_builder):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"x" * 8193

        mock_builder.return_value.open.return_value.__enter__.return_value = (
            response
        )

        with self.assertRaises(EnrollmentHTTPError):
            post_json("/api/v2/agents/register", {})

    @patch("agent.enrollment_http.urllib.request.build_opener")
    @patch("agent.enrollment_http.ssl.create_default_context")
    def test_reject_nonobject_response(self, mock_context, mock_builder):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"[]"

        mock_builder.return_value.open.return_value.__enter__.return_value = (
            response
        )

        with self.assertRaises(EnrollmentHTTPError):
            post_json("/api/v2/agents/register", {})


if __name__ == "__main__":
    unittest.main()
