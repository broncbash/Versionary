#!/usr/bin/env python3
"""Versionary transactional trust-state development foundation.

Not a production installer. Local SQLite history is not resistant
to privileged replacement, database snapshot rollback, or root compromise.
"""

import hashlib
import importlib.util
import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]


class TrustStateError(Exception):
    pass


def load_updates():
    spec = importlib.util.spec_from_file_location(
        "versionary_trust_state_updates",
        ROOT / "installer/release-policy-updates.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_UPDATES = load_updates()


def _authority_identity(raw):
    if not isinstance(raw, bytes) or len(raw) > 8192:
        raise TrustStateError("Invalid stored authority bytes")
    try:
        key = serialization.load_pem_public_key(raw)
    except (ValueError, TypeError) as exc:
        raise TrustStateError("Invalid stored authority key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise TrustStateError("Stored authority is not Ed25519")
    return _UPDATES.key_identity(key)


def _check_parent(path):
    parent = Path(path).parent
    if not parent.is_dir() or parent.is_symlink():
        raise TrustStateError("Unsafe trust-state directory")

    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise TrustStateError("Unsafe trust-state directory")

    if info.st_mode & 0o077:
        raise TrustStateError(
            "Trust-state directory must be private"
        )

    if info.st_uid != os.geteuid():
        raise TrustStateError(
            "Trust-state directory ownership mismatch"
        )


def _check_database(path):
    path = Path(path)
    _check_parent(path)
    if path.is_symlink():
        raise TrustStateError("Trust database cannot be a symlink")
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise TrustStateError("Trust database does not exist") from exc
    if not stat.S_ISREG(info.st_mode):
        raise TrustStateError("Trust database must be a regular file")
    if info.st_mode & 0o077:
        raise TrustStateError("Trust database permissions are too broad")
    return path


def connect(path):
    path = _check_database(path)
    before = path.stat()

    connection = sqlite3.connect(
        path.as_uri() + "?mode=rw",
        uri=True,
        timeout=10,
    )

    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")

        after = path.stat()
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
        ):
            raise TrustStateError(
                "Trust database changed during connection"
            )

        # Detect changes between pathname checks. This is not a
        # substitute for protecting the directory from hostile writers.
        return connection
    except Exception:
        connection.close()
        raise


def initialize(path, authority_path):
    """Explicit bootstrap with an independently supplied authority key."""
    authority_bytes = _UPDATES.read_regular(authority_path, 8192)
    identity = _authority_identity(authority_bytes)
    path = Path(path)

    # Exclusive creation prevents overwriting existing state.
    # Parent directory must already exist; no implicit directory creation.
    _check_parent(path)

    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_RDWR,
            0o600,
        )
    except FileExistsError as exc:
        raise TrustStateError(
            "Trust database already exists"
        ) from exc

    os.close(descriptor)

    try:
        with closing(connect(path)) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            with connection:
                connection.execute("""
                    CREATE TABLE trust_state (
                        singleton INTEGER PRIMARY KEY
                            CHECK (singleton = 1),
                        authority_key_id TEXT NOT NULL,
                        authority_public BLOB NOT NULL,
                        policy_version INTEGER NOT NULL
                            CHECK (policy_version >= 0),
                        policy_sha256 TEXT,
                        policy_bytes BLOB
                    )
                """)
                connection.execute("""
                    INSERT INTO trust_state VALUES
                    (1, ?, ?, 0, NULL, NULL)
                """, (identity, authority_bytes))
    except Exception:
        # Fail closed: leave a failed bootstrap artifact in place
        # rather than silently allowing another bootstrap.
        raise

    return identity


def current_state(connection):
    integrity = connection.execute(
        "PRAGMA quick_check"
    ).fetchone()
    if integrity != ("ok",):
        raise TrustStateError("Trust database integrity check failed")

    expected_columns = [
        "singleton", "authority_key_id", "authority_public",
        "policy_version", "policy_sha256", "policy_bytes",
    ]
    columns = [
        row[1] for row in connection.execute(
            "PRAGMA table_info(trust_state)"
        ).fetchall()
    ]
    if columns != expected_columns:
        raise TrustStateError("Unexpected trust-state schema")

    rows = connection.execute("""
        SELECT singleton, authority_key_id, authority_public,
               policy_version, policy_sha256, policy_bytes
        FROM trust_state
    """).fetchall()

    if len(rows) != 1 or rows[0][0] != 1:
        raise TrustStateError("Missing or inconsistent trust state")

    _, identity, authority, version, digest, policy = rows[0]

    if not isinstance(identity, str):
        raise TrustStateError("Invalid stored authority identity")
    if _authority_identity(authority) != identity:
        raise TrustStateError("Stored authority fingerprint mismatch")

    if type(version) is not int or not 0 <= version <= _UPDATES.MAX_VERSION:
        raise TrustStateError("Invalid stored policy version")

    if version == 0:
        if digest is not None or policy is not None:
            raise TrustStateError("Invalid bootstrap state")
    else:
        if not isinstance(policy, bytes):
            raise TrustStateError("Missing stored policy")
        if not isinstance(digest, str):
            raise TrustStateError("Missing stored policy digest")
        if hashlib.sha256(policy).hexdigest() != digest:
            raise TrustStateError("Stored policy digest mismatch")

        spec = importlib.util.spec_from_file_location(
            "versionary_state_policy_validator",
            ROOT / "installer/release-trust-policy.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_policy(_UPDATES.parse_json(policy))

    return {
        "authority_key_id": identity,
        "authority_public": authority,
        "policy_version": version,
        "policy_sha256": digest,
        "policy_bytes": policy,
    }


def install_update(database, policy_path, signature_path):
    """Serialize installers and atomically store authenticated bytes."""
    # Capture input files exactly once, before opening the transaction.
    policy = _UPDATES.read_regular(policy_path)
    signature = _UPDATES.read_regular(signature_path, 16384)

    with closing(connect(database)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            current = current_state(connection)

            version = _UPDATES.verify_update_bytes(
                policy,
                signature,
                current["authority_public"],
                current["policy_version"],
            )

            digest = hashlib.sha256(policy).hexdigest()
            result = connection.execute("""
                UPDATE trust_state
                SET policy_version = ?,
                    policy_sha256 = ?,
                    policy_bytes = ?
                WHERE singleton = 1
            """, (version, digest, policy))

            if result.rowcount != 1:
                raise TrustStateError("Trust-state update failed")

        return version


def read_state(database):
    with closing(connect(database)) as connection:
        return current_state(connection)
