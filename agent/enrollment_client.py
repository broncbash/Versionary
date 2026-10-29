"""Manual, recoverable enrollment for ARBY PATCH AGENT v2."""

import secrets
from pathlib import Path

from .credentials import (
    CredentialError,
    load_credential,
    save_credential,
)
from .enrollment_crypto import (
    hash_credential,
    sign_enrollment,
    decode_bytes,
)
from .enrollment_http import post_json
from .enrollment_journal import (
    load_journal,
    save_journal,
    delete_journal,
)
from .enrollment_keys import get_or_create_keypair


class EnrollmentClientError(RuntimeError):
    """Enrollment could not safely proceed."""


def register_v2(identity, *, key_path=None, post=post_json):
    """Register a persistent identity and public key for approval."""

    kwargs = {"path": key_path} if key_path is not None else {}
    keys = get_or_create_keypair(**kwargs)

    response = post(
        "/api/v2/agents/register",
        {
            "agent_id": identity["agent_id"],
            "hostname": identity["hostname"],
            "platform": identity["platform"],
            "public_key": keys["public_key"],
        },
    )

    if (
        response.get("agent_id") != identity["agent_id"]
        or response.get("status") != "pending"
    ):
        raise EnrollmentClientError(
            "Unexpected registration response"
        )

    return response


def complete_v2(
    identity,
    *,
    key_path=None,
    journal_path=None,
    credential_path=None,
    post=post_json,
):
    """Complete approved enrollment, recovering interrupted requests."""

    agent_id = identity["agent_id"]

    key_kwargs = {"path": key_path} if key_path is not None else {}
    journal_kwargs = (
        {"path": journal_path}
        if journal_path is not None else {}
    )
    credential_kwargs = (
        {"path": credential_path}
        if credential_path is not None else {}
    )

    keys = get_or_create_keypair(**key_kwargs)
    journal = load_journal(**journal_kwargs)

    try:
        installed_token = load_credential(**credential_kwargs)
    except CredentialError as exc:
        if "has not been provisioned" not in str(exc):
            raise
        installed_token = None

    if installed_token is not None:
        if journal is None:
            return {
                "agent_id": agent_id,
                "status": "already-provisioned",
            }

        if (
            journal["agent_id"] != agent_id
            or hash_credential(installed_token)
            != journal["credential_hash"]
        ):
            raise EnrollmentClientError(
                "Installed credential conflicts with enrollment journal"
            )

        response = post(
            f"/api/v2/agents/{agent_id}/complete",
            {
                "challenge": journal["challenge"],
                "signature": journal["signature"],
                "credential_hash": journal["credential_hash"],
            },
        )

        if (
            response.get("agent_id") != agent_id
            or response.get("status") != "enrolled"
            or not isinstance(response.get("recovered"), bool)
        ):
            raise EnrollmentClientError(
                "Server did not confirm enrollment recovery"
            )

        delete_journal(**journal_kwargs)
        return response

    if journal is None:
        response = post(
            f"/api/v2/agents/{agent_id}/challenge",
            {},
        )

        if response.get("agent_id") != agent_id:
            raise EnrollmentClientError(
                "Unexpected enrollment challenge identity"
            )

        challenge = response.get("challenge")
        decode_bytes(challenge, 32)

        token = secrets.token_urlsafe(48)
        credential_hash = hash_credential(token)

        journal = {
            "agent_id": agent_id,
            "challenge": challenge,
            "signature": sign_enrollment(
                keys["private_key"],
                agent_id,
                challenge,
                credential_hash,
            ),
            "credential_hash": credential_hash,
            "token": token,
        }

        save_journal(journal, **journal_kwargs)

    if journal["agent_id"] != agent_id:
        raise EnrollmentClientError(
            "Enrollment journal belongs to another agent"
        )

    response = post(
        f"/api/v2/agents/{agent_id}/complete",
        {
            "challenge": journal["challenge"],
            "signature": journal["signature"],
            "credential_hash": journal["credential_hash"],
        },
    )

    if (
        response.get("agent_id") != agent_id
        or response.get("status") != "enrolled"
        or not isinstance(response.get("recovered"), bool)
    ):
        raise EnrollmentClientError(
            "Unexpected enrollment completion response"
        )

    save_credential(journal["token"], **credential_kwargs)
    delete_journal(**journal_kwargs)

    return response
