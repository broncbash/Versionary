#!/usr/bin/env python3
"""Development-only authenticated, staged trust-database rebuild.

Requires a private directory and externally trusted authority and
version floor. Does not replace existing databases.
"""

import hashlib
import importlib.util
import os
import secrets
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state = load("release-trust-state.py", "versionary_rebuild_state")
updates = state._UPDATES


class RebuildError(Exception):
    pass


def rebuild(database, authority_path, policy_path,
            signature_path, minimum_version):
    if (
        type(minimum_version) is not int
        or not 1 <= minimum_version <= updates.MAX_VERSION
    ):
        raise RebuildError(
            "Rebuild requires a positive trusted minimum version"
        )

    database = Path(database)
    if not database.is_absolute() or database.name in ("", ".", ".."):
        raise RebuildError("Database path must be absolute")

    if database.exists() or database.is_symlink():
        raise RebuildError("Database already exists")

    state._check_parent(database)

    # Capture inputs exactly once, before creating any artifact.
    authority = updates.read_regular(authority_path, 8192)
    identity = state._authority_identity(authority)
    policy = updates.read_regular(policy_path)
    signature = updates.read_regular(signature_path, 16384)

    envelope, _ = updates.validate_envelope(signature)
    version = envelope["policy_version"]

    if version < minimum_version:
        raise RebuildError("Policy below trusted minimum version")

    verified = updates.verify_update_bytes(
        policy, signature, authority, 0
    )
    if verified != version:
        raise RebuildError("Policy version mismatch")

    digest = hashlib.sha256(policy).hexdigest()

    if not hasattr(os, "O_NOFOLLOW"):
        raise RebuildError("O_NOFOLLOW is required")

    directory_fd = os.open(
        database.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    stage_name = None

    try:
        directory_info = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(directory_info.st_mode)
            or directory_info.st_uid != os.geteuid()
            or directory_info.st_mode & 0o077
        ):
            raise RebuildError("Unsafe rebuild directory")

        # Keep the parent pinned and reject pathname replacement.
        current_parent = database.parent.lstat()
        if (
            current_parent.st_dev != directory_info.st_dev
            or current_parent.st_ino != directory_info.st_ino
        ):
            raise RebuildError("Rebuild directory changed")

        stage_name = ".versionary-rebuild-" + secrets.token_hex(16)
        descriptor = os.open(
            stage_name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        os.close(descriptor)

        # SQLite writes through the staged pathname. A hostile writer
        # with access to this directory remains outside our threat model.
        stage_path = database.parent / stage_name

        with closing(sqlite3.connect(stage_path)) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
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
                    (1, ?, ?, ?, ?, ?)
                """, (identity, authority, version, digest, policy))

        # Validate completed state before publishing it.
        record = state.read_state(stage_path)
        if (
            record["authority_key_id"] != identity
            or record["policy_version"] != version
            or record["policy_bytes"] != policy
        ):
            raise RebuildError("Staged trust-state verification failed")

        stage_fd = os.open(
            stage_name, os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        try:
            info = os.fstat(stage_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_uid != os.geteuid()
            ):
                raise RebuildError("Unsafe staging file")
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)

        # Exclusive publication: hard-link creation fails if the
        # destination exists, including a dangling symlink.
        try:
            os.link(
                stage_name,
                database.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise RebuildError("Database already exists") from exc

        os.fsync(directory_fd)
        os.unlink(stage_name, dir_fd=directory_fd)
        stage_name = None
        os.fsync(directory_fd)

        return {
            "status": "rebuilt",
            "authority_key_id": identity,
            "policy_version": version,
            "database": str(database),
        }

    finally:
        if stage_name is not None:
            try:
                os.unlink(stage_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.close(directory_fd)
