"""Secure v2 enrollment registration.

Registration and public-key binding happen atomically.
This module does not expose HTTP routes or issue credentials.
"""

import sqlite3
from contextlib import closing
from uuid import UUID

import agent_registry
from enrollment_crypto import decode_bytes
from enrollment_store import SCHEMA


class EnrollmentRegistrationError(ValueError):
    pass


class EnrollmentConflictError(EnrollmentRegistrationError):
    pass


def register_with_key(agent_id, hostname, platform, public_key):
    """Create a pending agent with an immutable Ed25519 public key."""

    try:
        agent_id = str(UUID(agent_id))
        decode_bytes(public_key, 32)
    except (ValueError, TypeError) as exc:
        raise EnrollmentRegistrationError(
            "Invalid agent identity or public key"
        ) from exc

    if not isinstance(hostname, str) or not hostname.strip():
        raise EnrollmentRegistrationError("Invalid hostname")

    if not isinstance(platform, str) or not platform.strip():
        raise EnrollmentRegistrationError("Invalid platform")

    hostname = hostname.strip()
    platform = platform.strip()

    if len(hostname) > 255 or len(platform) > 64:
        raise EnrollmentRegistrationError(
            "Agent metadata exceeds permitted length"
        )

    with closing(sqlite3.connect(agent_registry.DB_PATH)) as db:
        db.execute("PRAGMA foreign_keys = ON")

        try:
            with db:
                db.execute(SCHEMA)

                existing = db.execute(
                    "SELECT 1 FROM agents WHERE id = ?",
                    (agent_id,),
                ).fetchone()

                if existing:
                    raise EnrollmentConflictError(
                        "Agent identity already registered"
                    )

                db.execute(
                    """
                    INSERT INTO agents
                        (id, hostname, platform, status, registered_at)
                    VALUES (?, ?, ?, 'pending',
                            strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    """,
                    (agent_id, hostname, platform),
                )

                db.execute(
                    """
                    INSERT INTO agent_enrollments
                        (agent_id, public_key)
                    VALUES (?, ?)
                    """,
                    (agent_id, public_key),
                )

        except sqlite3.IntegrityError as exc:
            raise EnrollmentConflictError(
                "Agent registration conflict"
            ) from exc

    return {"agent_id": agent_id, "status": "pending"}
