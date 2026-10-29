"""Recoverable enrollment with credential-bound Ed25519 signatures."""

import hashlib
import hmac
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

import agent_registry
from enrollment_crypto import (
    decode_bytes,
    encode_bytes,
    EnrollmentCryptoError,
)
from enrollment_store import utc_now

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)


HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RECOVERY_WINDOW = timedelta(minutes=5)
DOMAIN = b"ARBY-PATCH-ENROLLMENT-V2:"


class RecoverableEnrollmentError(ValueError):
    """Enrollment proof or state is invalid."""


def enrollment_message(agent_id, challenge, credential_hash):
    """Construct a domain-separated, credential-bound message."""

    if not isinstance(agent_id, str):
        raise RecoverableEnrollmentError("Invalid agent ID")

    if not isinstance(credential_hash, str) or not HASH_PATTERN.fullmatch(
        credential_hash
    ):
        raise RecoverableEnrollmentError("Invalid credential hash")

    try:
        challenge_bytes = decode_bytes(challenge, 32)
    except EnrollmentCryptoError as exc:
        raise RecoverableEnrollmentError(
            "Invalid enrollment challenge"
        ) from exc

    return (
        DOMAIN
        + agent_id.encode("utf-8")
        + b":"
        + challenge_bytes
        + b":"
        + bytes.fromhex(credential_hash)
    )


def sign_enrollment(private_key, agent_id, challenge, credential_hash):
    """Sign the exact enrollment identity, challenge, and credential."""

    return encode_bytes(
        private_key.sign(
            enrollment_message(agent_id, challenge, credential_hash)
        )
    )


def verify_enrollment_signature(
    public_key, agent_id, challenge, credential_hash, signature
):
    try:
        key = Ed25519PublicKey.from_public_bytes(
            decode_bytes(public_key, 32)
        )
        signature_bytes = decode_bytes(signature, 64)
        key.verify(
            signature_bytes,
            enrollment_message(agent_id, challenge, credential_hash),
        )
        return True
    except (
        EnrollmentCryptoError,
        RecoverableEnrollmentError,
        InvalidSignature,
        ValueError,
        TypeError,
    ):
        return False


def complete_recoverable_enrollment(
    agent_id, challenge, signature, credential_hash
):
    """Issue or confirm one credential in a serialized transaction."""

    if not all(
        isinstance(value, str) and value
        for value in (agent_id, challenge, signature, credential_hash)
    ):
        raise RecoverableEnrollmentError("Invalid enrollment request")

    if not HASH_PATTERN.fullmatch(credential_hash):
        raise RecoverableEnrollmentError("Invalid credential hash")

    with closing(sqlite3.connect(
        agent_registry.DB_PATH, timeout=10
    )) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("BEGIN IMMEDIATE")

        try:
            row = db.execute(
                """
                SELECT e.public_key,
                       e.challenge,
                       e.challenge_expires,
                       e.completed_at,
                       a.status,
                       c.token_hash,
                       c.revoked_at
                FROM agent_enrollments e
                JOIN agents a ON a.id = e.agent_id
                LEFT JOIN agent_credentials c
                    ON c.agent_id = e.agent_id
                WHERE e.agent_id = ?
                """,
                (agent_id,),
            ).fetchone()

            if row is None:
                raise RecoverableEnrollmentError(
                    "Enrollment unavailable"
                )

            (
                public_key,
                stored_challenge,
                expires,
                completed_at,
                status,
                stored_hash,
                revoked_at,
            ) = row

            if status != "approved" or revoked_at is not None:
                raise RecoverableEnrollmentError("Agent not approved")

            if not hmac.compare_digest(
                stored_challenge or "", challenge
            ):
                raise RecoverableEnrollmentError(
                    "Enrollment challenge mismatch"
                )

            if not verify_enrollment_signature(
                public_key,
                agent_id,
                challenge,
                credential_hash,
                signature,
            ):
                raise RecoverableEnrollmentError(
                    "Invalid enrollment signature"
                )

            now = utc_now()

            if completed_at is not None:
                try:
                    completed = datetime.fromisoformat(completed_at)
                    if (
                        completed.tzinfo is None
                        or now > completed + RECOVERY_WINDOW
                    ):
                        raise RecoverableEnrollmentError(
                            "Recovery window expired"
                        )
                except ValueError as exc:
                    raise RecoverableEnrollmentError(
                        "Invalid completion timestamp"
                    ) from exc

                if (
                    stored_hash is None
                    or not hmac.compare_digest(
                        stored_hash, credential_hash
                    )
                ):
                    raise RecoverableEnrollmentError(
                        "Enrollment already completed"
                    )

                db.commit()
                return {
                    "agent_id": agent_id,
                    "status": "enrolled",
                    "recovered": True,
                }

            if stored_hash is not None:
                raise RecoverableEnrollmentError(
                    "Agent already has a credential"
                )

            if not expires:
                raise RecoverableEnrollmentError(
                    "No active challenge"
                )

            try:
                expiration = datetime.fromisoformat(expires)
                if expiration.tzinfo is None or expiration <= now:
                    raise RecoverableEnrollmentError(
                        "Enrollment challenge expired"
                    )
            except ValueError as exc:
                raise RecoverableEnrollmentError(
                    "Invalid challenge expiration"
                ) from exc

            db.execute(
                """
                INSERT INTO agent_credentials
                    (agent_id, token_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (agent_id, credential_hash, now.isoformat()),
            )

            db.execute(
                """
                UPDATE agent_enrollments
                SET completed_at = ?
                WHERE agent_id = ?
                  AND completed_at IS NULL
                """,
                (now.isoformat(), agent_id),
            )

            db.commit()

            return {
                "agent_id": agent_id,
                "status": "enrolled",
                "recovered": False,
            }

        except Exception:
            db.rollback()
            raise
