import sqlite3
import json
from report_validation import validate_packages
from pathlib import Path
from contextlib import closing
from agent_auth import (
    generate_agent_token,
    hash_agent_token,
    verify_agent_token,
)

DB_PATH = Path("/var/lib/arby-patch-command/agents.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'revoked')),
    registered_at TEXT NOT NULL,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS scan_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    count INTEGER,
    packages_json TEXT NOT NULL,
    error TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_reports_agent
ON scan_reports(agent_id, timestamp);

CREATE TABLE IF NOT EXISTS agent_credentials (
    agent_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
"""


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)

from datetime import datetime, timezone
from uuid import UUID, uuid4


def register_agent(
    hostname: str,
    platform: str,
    agent_id: str | None = None,
) -> str:

    """Register a new agent in pending state."""

    hostname = hostname.strip()
    platform = platform.strip()

    if not hostname or not platform:
        raise ValueError("Hostname and platform are required")

    if len(hostname) > 255 or len(platform) > 64:
        raise ValueError("Hostname or platform exceeds allowed length")

    if agent_id is None:
        agent_id = str(uuid4())
    else:
        try:
            agent_id = str(UUID(agent_id))
        except (ValueError, AttributeError, TypeError):
            raise ValueError("Invalid agent ID") from None

    timestamp = datetime.now(timezone.utc).isoformat()

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute(
            """
            INSERT INTO agents
                (id, hostname, platform, status, registered_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (agent_id, hostname, platform, timestamp),
        )

    return agent_id


def approve_agent(agent_id: str) -> bool:
    """Approve a pending agent only."""

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        result = db.execute(
            """
            UPDATE agents
            SET status = 'approved'
            WHERE id = ? AND status = 'pending'
            """,
            (agent_id,),
        )

        return result.rowcount == 1


def revoke_agent(agent_id: str) -> bool:
    """Revoke an agent permanently within its current identity."""

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        result = db.execute(
            """
            UPDATE agents
            SET status = 'revoked'
            WHERE id = ? AND status != 'revoked'
            """,
            (agent_id,),
        )

        return result.rowcount == 1


def is_agent_approved(agent_id: str) -> bool:
    """Check whether an agent is approved."""

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        row = db.execute(
            "SELECT status FROM agents WHERE id = ?",
            (agent_id,),
        ).fetchone()

    return row is not None and row[0] == "approved"

def issue_agent_credential(agent_id: str) -> str | None:
    """Issue a credential only to an approved agent."""

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        db.execute("PRAGMA foreign_keys = ON")

        row = db.execute(
            "SELECT status FROM agents WHERE id = ?",
            (agent_id,),
        ).fetchone()

        if row is None or row[0] != "approved":
            return None

        token = generate_agent_token()
        token_hash = hash_agent_token(token)
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            db.execute(
                """
                INSERT INTO agent_credentials
                    (agent_id, token_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (agent_id, token_hash, timestamp),
            )
        except sqlite3.IntegrityError:
            return None

    return token

def authenticate_agent(agent_id: str, token: str) -> bool:
    """Authenticate an approved agent with an active credential."""

    if not agent_id or not token:
        return False

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        row = db.execute(
            """
            SELECT a.status, c.token_hash, c.revoked_at
            FROM agents AS a
            JOIN agent_credentials AS c
                ON c.agent_id = a.id
            WHERE a.id = ?
            """,
            (agent_id,),
        ).fetchone()

    if row is None:
        return False

    status, stored_hash, revoked_at = row

    if status != "approved" or revoked_at is not None:
        return False

    return verify_agent_token(token, stored_hash)

def record_agent_heartbeat(agent_id: str, token: str) -> bool:
    """Record a heartbeat from an authenticated agent."""

    if not agent_id or not token:
        return False

    if not authenticate_agent(agent_id, token):
        return False

    timestamp = datetime.now(timezone.utc).isoformat()

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        cursor = db.execute(
            """
            UPDATE agents
            SET last_seen = ?
            WHERE id = ?
              AND status = 'approved'
              AND EXISTS (
                  SELECT 1
                  FROM agent_credentials
                  WHERE agent_id = agents.id
                    AND revoked_at IS NULL
                    AND token_hash = ?
              )
            """,
            (timestamp, agent_id, hash_agent_token(token)),
        )

        return cursor.rowcount == 1

def record_agent_scan(
    agent_id: str,
    token: str,
    status: str,
    packages: list,
    error: str | None = None,
) -> bool:
    """Store a scan report from an authenticated agent."""

    if not agent_id or not token:
        return False

    if status not in ("success", "error"):
        return False

    validated_packages = validate_packages(packages)

    if validated_packages is None:
        return False

    packages_json = json.dumps(
        validated_packages,
        allow_nan=False,
    )


    if not authenticate_agent(agent_id, token):
        return False

    timestamp = datetime.now(timezone.utc).isoformat()

    with closing(sqlite3.connect(DB_PATH)) as db, db:
        cursor = db.execute(
            """
            INSERT INTO scan_reports
                (agent_id, timestamp, status,
                 count, packages_json, error)
            SELECT
                a.id, ?, ?, ?, ?, ?
            FROM agents AS a
            JOIN agent_credentials AS c
                ON c.agent_id = a.id
            WHERE a.id = ?
              AND a.status = 'approved'
              AND c.revoked_at IS NULL
              AND c.token_hash = ?
            """,
            (
                timestamp,
                status,
                len(validated_packages) if status == "success" else None,
                packages_json,
                error,
                agent_id,
                hash_agent_token(token),
            ),
        )

        return cursor.rowcount == 1
