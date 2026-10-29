"""Persistent enrollment state for ARBY PATCH COMMAND.

All enrollment operations use the existing SQLite registry database.
No production schema changes occur until explicitly initialized.
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import agent_registry
from enrollment_crypto import (
    decode_bytes,
    generate_challenge,
)


CHALLENGE_LIFETIME = timedelta(minutes=5)

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_enrollments (
    agent_id TEXT PRIMARY KEY,
    public_key TEXT NOT NULL,
    challenge TEXT,
    challenge_expires TEXT,
    completed_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
"""


def utc_now():
    return datetime.now(timezone.utc)


def initialize_enrollment_database():
    with closing(sqlite3.connect(agent_registry.DB_PATH)) as db:
        db.execute("PRAGMA foreign_keys = ON")
        with db:
            db.execute(SCHEMA)


def create_challenge(agent_id):
    """Return an active challenge or create a new five-minute one.

    The transaction serializes concurrent requests and prevents
    replacing a challenge while enrollment is in progress.
    """

    now = utc_now()

    with closing(sqlite3.connect(
        agent_registry.DB_PATH,
        timeout=10,
    )) as db:
        db.execute("BEGIN IMMEDIATE")

        try:
            row = db.execute(
                """
                SELECT e.challenge, e.challenge_expires
                FROM agent_enrollments e
                JOIN agents a ON a.id = e.agent_id
                WHERE e.agent_id = ?
                  AND a.status = 'approved'
                  AND e.completed_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM agent_credentials
                      WHERE agent_id = e.agent_id
                  )
                """,
                (agent_id,),
            ).fetchone()

            if row is None:
                db.rollback()
                return None

            challenge, expires = row

            if challenge and expires:
                try:
                    expiration = datetime.fromisoformat(expires)
                    if (
                        expiration.tzinfo is not None
                        and expiration > now
                    ):
                        db.commit()
                        return challenge
                except ValueError:
                    pass

            challenge = generate_challenge()
            expiration = (
                now + CHALLENGE_LIFETIME
            ).isoformat()

            db.execute(
                """
                UPDATE agent_enrollments
                SET challenge = ?,
                    challenge_expires = ?
                WHERE agent_id = ?
                """,
                (challenge, expiration, agent_id),
            )

            db.commit()
            return challenge

        except Exception:
            db.rollback()
            raise


def get_active_challenge(agent_id):
    """Return public key and challenge only while valid."""

    with closing(sqlite3.connect(agent_registry.DB_PATH)) as db:
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
                  SELECT 1 FROM agent_credentials
                  WHERE agent_id = e.agent_id
              )
            """,
            (agent_id,),
        ).fetchone()

    if row is None or not row[1] or not row[2]:
        return None

    try:
        expiration = datetime.fromisoformat(row[2])
        if expiration.tzinfo is None:
            return None
        if expiration <= utc_now():
            return None
    except ValueError:
        return None

    return {
        "public_key": row[0],
        "challenge": row[1],
    }


def consume_challenge(agent_id, challenge):
    """Atomically invalidate a matching, unexpired challenge.

    This primitive does not issue credentials. The eventual
    credential-issuance transaction must combine proof validation,
    challenge consumption, and credential creation atomically.
    """

    now = utc_now()

    with closing(sqlite3.connect(agent_registry.DB_PATH)) as db:
        with db:
            cursor = db.execute(
                """
                UPDATE agent_enrollments
                SET challenge = NULL,
                    challenge_expires = NULL
                WHERE agent_id = ?
                  AND challenge = ?
                  AND challenge_expires > ?
                  AND completed_at IS NULL
                  AND EXISTS (
                      SELECT 1 FROM agents
                      WHERE id = agent_enrollments.agent_id
                        AND status = 'approved'
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM agent_credentials
                      WHERE agent_id = agent_enrollments.agent_id
                  )
                """,
                (agent_id, challenge, now.isoformat()),
            )

            return cursor.rowcount == 1
