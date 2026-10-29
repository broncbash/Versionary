"""Authenticated update reporting for ARBY PATCH AGENT."""

import json
import ssl
import urllib.error
import urllib.request
import uuid

from agent.credentials import validate_token
from agent.config import connection


MAX_PACKAGES = 5000
MAX_REPORT_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 8192


class ReportingError(RuntimeError):
    """Agent update reporting failed."""


def validate_report(report):
    """Validate an update report before transmission."""

    if not isinstance(report, dict):
        raise ReportingError("Invalid report format")

    if report.get("status") not in ("success", "error"):
        raise ReportingError("Invalid report status")

    packages = report.get("packages")

    if not isinstance(packages, list):
        raise ReportingError("Invalid package list")

    if len(packages) > MAX_PACKAGES:
        raise ReportingError("Too many packages")

    for package in packages:
        if not isinstance(package, dict):
            raise ReportingError("Invalid package entry")

        for field, limit in (
            ("name", 256),
            ("installed", 128),
            ("available", 128),
        ):
            value = package.get(field)

            if (
                not isinstance(value, str)
                or not 1 <= len(value) <= limit
            ):
                raise ReportingError(
                    f"Invalid package field: {field}"
                )

        repository = package.get("repository")

        if repository is not None and (
            not isinstance(repository, str)
            or len(repository) > 256
        ):
            raise ReportingError("Invalid repository")

    error = report.get("error")

    if error is not None and (
        not isinstance(error, str)
        or len(error) > 4096
    ):
        raise ReportingError("Invalid report error field")

    try:
        payload = json.dumps(
            {
                "status": report["status"],
                "packages": packages,
                "error": error,
            },
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ReportingError("Report cannot be serialized") from None

    if len(payload) > MAX_REPORT_BYTES:
        raise ReportingError("Report exceeds size limit")

    return payload


def send_report(
    identity,
    token,
    report,
    server=None,
    ca_cert=None,
):
    """Send an authenticated update report over HTTPS."""

    if server is not None and not server.startswith("https://"):
        raise ReportingError("HTTPS is required")
    server, ca_cert = connection(server, ca_cert)
    if not server.startswith("https://"):
        raise ReportingError("HTTPS is required")

    try:
        agent_id = str(uuid.UUID(identity["agent_id"]))
        validate_token(token)
    except (KeyError, ValueError, TypeError, RuntimeError):
        raise ReportingError(
            "Invalid agent identity or credential"
        ) from None

    payload = validate_report(report)

    try:
        context = ssl.create_default_context(
            cafile=str(ca_cert)
        )

        request = urllib.request.Request(
            server.rstrip("/")
            + f"/api/v1/agents/{agent_id}/report",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            context=context,
            timeout=30,
        ) as response:
            if response.status != 201:
                raise ReportingError(
                    "Unexpected reporting HTTP status"
                )

            data = response.read(MAX_RESPONSE_BYTES + 1)

            if len(data) > MAX_RESPONSE_BYTES:
                raise ReportingError(
                    "Reporting response is too large"
                )

            result = json.loads(data)

    except urllib.error.HTTPError as exc:
        try:
            if exc.code == 401:
                message = "Agent authentication rejected"
            elif exc.code == 403:
                message = "Agent is not authorized"
            elif exc.code == 503:
                message = "Agent reporting is disabled"
            elif exc.code == 422:
                message = "Server rejected the report format"
            else:
                message = f"Reporting failed: HTTP {exc.code}"
        finally:
            exc.close()

        raise ReportingError(message) from None

    except (urllib.error.URLError, OSError, ssl.SSLError):
        raise ReportingError(
            "Secure connection to PATCH COMMAND failed"
        ) from None

    except (ValueError, UnicodeError):
        raise ReportingError(
            "Invalid reporting response"
        ) from None

    if (
        not isinstance(result, dict)
        or result.get("status") != "recorded"
    ):
        raise ReportingError(
            "Unexpected reporting acknowledgment"
        )

    return result
