"""Tests for authenticated ARBY PATCH AGENT reporting."""


import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from agent.reporting import (
    ReportingError,
    send_report,
    validate_report,
)


IDENTITY = {
    "agent_id": "00000000-0000-4000-8000-000000000001",
    "hostname": "monitoring",
    "platform": "arch",
}

REPORT = {
    "status": "success",
    "packages": [{
        "name": "linux",
        "installed": "6.11",
        "available": "6.12",
    }],
    "error": None,
}


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=201):
        super().__init__(payload)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestReportingClient(unittest.TestCase):
    def setUp(self):
        self._config_patch = unittest.mock.patch("agent.config.load_config", return_value={"server": "https://example.test", "ca_cert": "/tmp/arby-test-ca.crt"})
        self._config_patch.start()
        self.addCleanup(self._config_patch.stop)


    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
    def test_success(self, builder, context):
        builder.return_value.open.return_value = FakeResponse(
            b'{"status":"recorded"}'
        )

        result = send_report(
            IDENTITY, "test-token", REPORT
        )

        self.assertEqual(result["status"], "recorded")

        request = builder.return_value.open.call_args.args[0]

        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer test-token",
        )

        self.assertEqual(request.get_method(), "POST")

        self.assertEqual(
            json.loads(request.data)["packages"][0]["name"],
            "linux",
        )

        context.assert_called_once()

    def test_reject_http(self):
        with self.assertRaisesRegex(
            ReportingError, "HTTPS is required"
        ):
            send_report(
                IDENTITY,
                "test-token",
                REPORT,
                server="http://192.168.86.15",
            )

    def test_invalid_token(self):
        with self.assertRaisesRegex(
            ReportingError, "Invalid agent identity or credential"
        ):
            send_report(IDENTITY, "bad\nsecret", REPORT)

    def test_invalid_status(self):
        with self.assertRaisesRegex(
            ReportingError, "Invalid report status"
        ):
            validate_report({
                "status": "unknown",
                "packages": [],
            })

    def test_invalid_package(self):
        with self.assertRaisesRegex(
            ReportingError, "Invalid package field"
        ):
            validate_report({
                "status": "success",
                "packages": [{"name": 123}],
            })

    def test_too_many_packages(self):
        with self.assertRaisesRegex(
            ReportingError, "Too many packages"
        ):
            validate_report({
                "status": "success",
                "packages": [{}] * 5001,
            })

    @patch("agent.reporting.MAX_REPORT_BYTES", 20)
    def test_oversized_report(self):
        with self.assertRaisesRegex(
            ReportingError, "size limit"
        ):
            validate_report(REPORT)

    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
    def test_authentication_rejected(self, builder, _context):
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
            ReportingError, "authentication rejected"
        ):
            send_report(IDENTITY, "test-token", REPORT)

    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
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
            ReportingError, "reporting is disabled"
        ):
            send_report(IDENTITY, "test-token", REPORT)

    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
    def test_invalid_acknowledgment(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            b'{"status":"unexpected"}'
        )

        with self.assertRaisesRegex(
            ReportingError, "Unexpected reporting acknowledgment"
        ):
            send_report(IDENTITY, "test-token", REPORT)

    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
    def test_oversized_response(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            b"x" * 8193
        )

        with self.assertRaisesRegex(
            ReportingError, "response is too large"
        ):
            send_report(IDENTITY, "test-token", REPORT)

    @patch("agent.reporting.ssl.create_default_context")
    @patch("agent.reporting.urllib.request.build_opener")
    def test_unexpected_http_status(self, builder, _context):
        builder.return_value.open.return_value = FakeResponse(
            b'{"status":"recorded"}',
            status=200,
        )

        with self.assertRaisesRegex(
            ReportingError, "Unexpected reporting HTTP status"
        ):
            send_report(IDENTITY, "test-token", REPORT)


if __name__ == "__main__":
    unittest.main()
