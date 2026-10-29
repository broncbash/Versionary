"""Authenticated HTTPS heartbeat for ARBY PATCH AGENT."""

import json
import ssl
import urllib.error
import urllib.request
import uuid

from agent.credentials import validate_token
from agent.config import connection


class HeartbeatError(RuntimeError):
    """Heartbeat request failed."""


def send_heartbeat(
    identity,
    token,
    server=None,
    ca_cert=None,
):
    """Send an authenticated heartbeat to PATCH COMMAND."""

    if server is not None and not server.startswith("https://"):
        raise HeartbeatError("HTTPS is required")
    server, ca_cert = connection(server, ca_cert)
    if not server.startswith("https://"):
        raise HeartbeatError("HTTPS is required")

    try:
        agent_id = str(uuid.UUID(identity["agent_id"]))
        validate_token(token)
    except (KeyError, ValueError, TypeError) as exc:
        raise HeartbeatError(
            "Invalid agent identity or credential"
        ) from exc
    except RuntimeError as exc:
        raise HeartbeatError(
            "Invalid agent identity or credential"
        ) from exc

    try:
        context = ssl.create_default_context(
            cafile=str(ca_cert)
        )

        request = urllib.request.Request(
            server.rstrip("/")
            + f"/api/v1/agents/{agent_id}/heartbeat",
            data=b"{}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            context=context,
            timeout=15,
        ) as response:
            if response.status != 200:
                raise HeartbeatError(
                    "Unexpected heartbeat HTTP status"
                )

            payload = response.read(8193)

            if len(payload) > 8192:
                raise HeartbeatError(
                    "Heartbeat response is too large"
                )

            result = json.loads(payload)

    except urllib.error.HTTPError as exc:
        try:
            if exc.code == 401:
                message = "Agent authentication rejected"
            elif exc.code == 403:
                message = "Agent is not authorized"
            elif exc.code == 503:
                message = "Agent reporting is disabled"
            else:
                message = f"Heartbeat failed: HTTP {exc.code}"
        finally:
            exc.close()

        raise HeartbeatError(message) from None

    except (
        urllib.error.URLError,
        OSError,
        ssl.SSLError,
    ):
        raise HeartbeatError(
            "Secure connection to PATCH COMMAND failed"
        ) from None

    except (ValueError, UnicodeError):
        raise HeartbeatError(
            "Invalid heartbeat response"
        ) from None

    if not isinstance(result, dict):
        raise HeartbeatError(
            "Invalid heartbeat response"
        )

    return result
