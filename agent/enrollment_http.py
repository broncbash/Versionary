"""Verified HTTPS transport for ARBY PATCH AGENT enrollment v2."""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from .config import connection


MAX_RESPONSE_BYTES = 8192


class EnrollmentHTTPError(RuntimeError):
    """Secure enrollment request failed."""


def post_json(path, payload, server=None,
              ca_cert=None):
    """POST JSON over verified HTTPS and return a bounded JSON object."""

    # Validate endpoint before reading local configuration.
    if not path.startswith("/api/v2/agents/"):
        raise EnrollmentHTTPError("Invalid enrollment endpoint")
    if server is not None:
        try:
            from .config import validate_server
            validate_server(server)
        except RuntimeError as exc:
            raise EnrollmentHTTPError(str(exc)) from None
    server, ca_cert = connection(server, ca_cert)
    parsed = urllib.parse.urlsplit(server)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise EnrollmentHTTPError("Invalid HTTPS server URL")

    if not path.startswith("/api/v2/agents/"):
        raise EnrollmentHTTPError("Invalid enrollment endpoint")

    try:
        context = ssl.create_default_context(cafile=str(ca_cert))

        request = urllib.request.Request(
            server.rstrip("/") + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # Enrollment must not follow redirects to another destination.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers,
                                 newurl):
                return None

        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            NoRedirect(),
        )

        with opener.open(request, timeout=15) as response:
            if response.status not in (200, 201):
                raise EnrollmentHTTPError(
                    "Unexpected enrollment response status"
                )

            raw = response.read(MAX_RESPONSE_BYTES + 1)

            if len(raw) > MAX_RESPONSE_BYTES:
                raise EnrollmentHTTPError(
                    "Enrollment response exceeds size limit"
                )

            result = json.loads(raw)

    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()

        if code == 409:
            message = "Enrollment unavailable or already registered"
        elif code == 422:
            message = "Enrollment request rejected"
        elif code == 503:
            message = "Enrollment v2 is disabled"
        else:
            message = f"Enrollment request failed: HTTP {code}"

        raise EnrollmentHTTPError(message) from None

    except (urllib.error.URLError, OSError, ssl.SSLError):
        raise EnrollmentHTTPError(
            "Secure connection to PATCH COMMAND failed"
        ) from None

    except (ValueError, UnicodeError, TypeError):
        raise EnrollmentHTTPError(
            "Invalid enrollment server response"
        ) from None

    if not isinstance(result, dict):
        raise EnrollmentHTTPError(
            "Enrollment server returned an invalid object"
        )

    return result
