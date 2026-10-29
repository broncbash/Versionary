"""Atomic Ed25519 enrollment completion and credential issuance."""

import hashlib
import secrets
import sqlite3
from contextlib import closing

import agent_registry
from enrollment_crypto import verify_challenge
from enrollment_store import utc_now


class EnrollmentCompletionError(ValueError):
    """Enrollment cannot be completed."""


def complete_enrollment(agent_id, challenge, signature):
    """Verify proof and issue exactly one credential atomically.

    Returns a plaintext token once, after a successful commit.
    The database stores only its SHA-256 hash.
    """

    if not all(
        isinstance(value, str) and value
        for value in (agent_id, challenge, signature)
    ):
        raise EnrollmentCompletionError(
            "Invalid enrollment proof"
        )

    with closing(sqlite3.connect(
        agent_registry.DB_PATH,
        timeout=10,
    )) as db:

        db.execute("PRAGMA foreign_keys = ON")

        # Acquire the write lock before checking any enrollment state.
        # Concurrent completion attempts are serialized.
        db.execute("BEGIN IMMEDIATE")

        try:
            row = db.execute(
                """
                SELECT e.public_key,
                       e.challenge,
                       e.challenge_expires
                FROM agent_enrollments e
                JOIN agents a ON a.id = e.agent_id
                WHERE e.agent_id = ?
                  AND a.status = 'approved'
                  AND e.completed_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM agent_credentials c
                      WHERE c.agent_id = e.agent_id
                  )
                """,
                (agent_id,),
            ).fetchone()

            if row is None:
                raise EnrollmentCompletionError(
                    "Enrollment unavailable"
                )

            public_key, stored_challenge, expires = row

            if not stored_challenge or not expires:
                raise EnrollmentCompletionError(
                    "No active enrollment challenge"
                )

            now = utc_now()

            try:
                from datetime import datetime

                expiration = datetime.fromisoformat(expires)
                if expiration.tzinfo is None or expiration <= now:
                    raise EnrollmentCompletionError(
                        "Enrollment challenge expired"
                    )
            except ValueError as exc:
                raise EnrollmentCompletionError(
                    "Invalid enrollment expiration"
                ) from exc

            if stored_challenge != challenge:
                raise EnrollmentCompletionError(
                    "Enrollment challenge mismatch"
                )

            if not verify_challenge(
                public_key, challenge, signature
            ):
                raise EnrollmentCompletionError(
                    "Invalid enrollment signature"
                )

            token = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(
                token.encode("utf-8")
            ).hexdigest()

            # Match the existing credential table schema.
            db.execute(
                """
                INSERT INTO agent_credentials
                    (agent_id, token_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (agent_id, token_hash, now.isoformat()),
            )

            db.execute(
                """
                UPDATE agent_enrollments
                SET challenge = NULL,
                    challenge_expires = NULL,
                    completed_at = ?
                WHERE agent_id = ?
                """,
                (now.isoformat(), agent_id),
            )

            db.commit()

            return {
                "agent_id": agent_id,
                "token": token,
                "status": "enrolled",
            }

        except Exception:
            db.rollback()
            raise
