"""Secure HTTPS registration for ARBY PATCH AGENT."""

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from .config import connection


DEFAULT_SERVER = None
DEFAULT_CA_CERT = Path(
    "/etc/arby-patch-agent/ca.crt"
)


class RegistrationError(RuntimeError):
    """Registration could not be completed."""


def register_agent(
    identity,
    server=None,
    ca_cert=None,
):
    """Submit an agent identity for manual approval."""

    if server is not None and not server.startswith("https://"):
        raise RegistrationError("HTTPS is required")
    server, ca_cert = connection(server, ca_cert)

    if not server.startswith("https://"):
        raise RegistrationError(
            "PATCH COMMAND requires HTTPS"
        )

    context = ssl.create_default_context(
        cafile=str(ca_cert)
    )

    payload = json.dumps({
        "agent_id": identity["agent_id"],
        "hostname": identity["hostname"],
        "platform": identity["platform"],
    }).encode("utf-8")

    request = urllib.request.Request(
        server.rstrip("/") + "/api/v1/agents/register",
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            context=context,
            timeout=15,
        ) as response:
            result = json.load(response)

    except urllib.error.HTTPError as exc:
        if exc.code == 503:
            raise RegistrationError(
                "Agent registration is disabled on the server"
            ) from exc

        if exc.code == 409:
            raise RegistrationError(
                "Agent identity is already registered"
            ) from exc

        raise RegistrationError(
            f"Registration failed: HTTP {exc.code}"
        ) from exc

    except (urllib.error.URLError, OSError) as exc:
        raise RegistrationError(
            f"HTTPS connection failed: {exc}"
        ) from exc

    if result.get("agent_id") != identity["agent_id"]:
        raise RegistrationError(
            "Server returned an unexpected agent identity"
        )

    if result.get("status") != "pending":
        raise RegistrationError(
            "Unexpected registration status"
        )

    return result
