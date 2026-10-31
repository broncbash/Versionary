#!/usr/bin/env python3
"""Development-only Versionary trust-state export.

Exports are integrity-checked snapshots, NOT authenticated
proof of freshness or authorization to restore a trust database.
"""

import hashlib
import importlib.util
import json
import os
import stat
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "versionary_export_state",
    ROOT / "installer/release-trust-state.py",
)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

SCHEMA_VERSION = 1
MAX_EXPORT_BYTES = 2 * 1024 * 1024


class TrustExportError(Exception):
    pass


def _private_directory(destination):
    parent = destination.parent

    if not parent.is_absolute():
        raise TrustExportError("Destination must be absolute")

    if parent.is_symlink() or not parent.is_dir():
        raise TrustExportError("Unsafe export directory")

    info = parent.stat()

    if not stat.S_ISDIR(info.st_mode):
        raise TrustExportError("Export directory must be regular")

    if info.st_uid != os.geteuid():
        raise TrustExportError("Export directory owner mismatch")

    if info.st_mode & 0o077:
        raise TrustExportError("Export directory must be private")

    return parent


def snapshot(database):
    """Read validated state inside one SQLite read transaction."""
    with closing(state.connect(Path(database))) as connection:
        try:
            connection.execute("BEGIN")
            record = state.current_state(connection)

            authority = record["authority_public"]
            policy = record["policy_bytes"]

            result = {
                "schema_version": SCHEMA_VERSION,
                "product": "Versionary",
                "artifact_type": "trust-state-snapshot",
                "authority_key_id": record["authority_key_id"],
                "authority_public_pem": authority.decode("ascii"),
                "policy_version": record["policy_version"],
                "policy_sha256": record["policy_sha256"],
                "policy_bytes_hex": (
                    policy.hex() if policy is not None else None
                ),
            }

            connection.commit()
            return result

        except Exception:
            connection.rollback()
            raise


def encode_snapshot(record):
    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    if len(payload) > MAX_EXPORT_BYTES:
        raise TrustExportError("Export exceeds maximum size")

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "payload": record,
    }

    raw = (
        json.dumps(
            envelope,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ) + "\n"
    ).encode("utf-8")

    if len(raw) > MAX_EXPORT_BYTES:
        raise TrustExportError("Export exceeds maximum size")

    return raw


def validate_export_bytes(raw):
    """Check snapshot structure and integrity, not authenticity."""
    if not isinstance(raw, bytes) or len(raw) > MAX_EXPORT_BYTES:
        raise TrustExportError("Invalid export size")

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise TrustExportError("Duplicate JSON field")
            result[key] = value
        return result

    try:
        envelope = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise TrustExportError("Invalid export JSON") from exc

    if not isinstance(envelope, dict) or set(envelope) != {
        "schema_version", "payload_sha256", "payload"
    }:
        raise TrustExportError("Invalid export envelope")

    if type(envelope["schema_version"]) is not int or (
        envelope["schema_version"] != SCHEMA_VERSION
    ):
        raise TrustExportError("Unsupported export schema")

    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise TrustExportError("Invalid export payload")

    required = {
        "schema_version", "product", "artifact_type",
        "authority_key_id", "authority_public_pem",
        "policy_version", "policy_sha256", "policy_bytes_hex",
    }

    if set(payload) != required:
        raise TrustExportError("Unexpected export fields")

    if type(payload["schema_version"]) is not int or (
        payload["schema_version"] != SCHEMA_VERSION
    ):
        raise TrustExportError("Invalid payload schema")

    if payload["product"] != "Versionary" or (
        payload["artifact_type"] != "trust-state-snapshot"
    ):
        raise TrustExportError("Invalid export identity")

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    digest = hashlib.sha256(canonical).hexdigest()

    if digest != envelope["payload_sha256"]:
        raise TrustExportError("Export digest mismatch")

    try:
        authority = payload["authority_public_pem"].encode("ascii")
        identity = state._authority_identity(authority)
    except (AttributeError, UnicodeError, TypeError, ValueError) as exc:
        raise TrustExportError("Invalid authority") from exc
    except state.TrustStateError as exc:
        raise TrustExportError("Invalid authority") from exc

    if identity != payload["authority_key_id"]:
        raise TrustExportError("Authority identity mismatch")

    version = payload["policy_version"]

    if type(version) is not int or not (
        0 <= version <= state._UPDATES.MAX_VERSION
    ):
        raise TrustExportError("Invalid policy version")

    if version == 0:
        if payload["policy_sha256"] is not None or (
            payload["policy_bytes_hex"] is not None
        ):
            raise TrustExportError("Invalid bootstrap snapshot")
    else:
        encoded = payload["policy_bytes_hex"]
        digest = payload["policy_sha256"]

        if not isinstance(encoded, str) or (
            not isinstance(digest, str)
        ):
            raise TrustExportError("Missing policy data")

        try:
            policy = bytes.fromhex(encoded)
        except ValueError as exc:
            raise TrustExportError("Invalid policy encoding") from exc

        if hashlib.sha256(policy).hexdigest() != digest:
            raise TrustExportError("Policy digest mismatch")

        if len(policy) > state._UPDATES.MAX_BYTES:
            raise TrustExportError("Policy exceeds size limit")

        # This checks policy structure, NOT an authority signature.
        try:
            spec = importlib.util.spec_from_file_location(
                "versionary_export_policy",
                ROOT / "installer/release-trust-policy.py",
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.validate_policy(state._UPDATES.parse_json(policy))
        except (ValueError, TypeError, KeyError) as exc:
            raise TrustExportError("Invalid policy structure") from exc

    return payload


def export_state(database, destination):
    """Create an exclusive owner-only snapshot; never overwrite."""
    destination = Path(destination)

    if not destination.is_absolute():
        raise TrustExportError("Export destination must be absolute")

    _private_directory(destination)

    # Validate and serialize before creating any output file.
    raw = encode_snapshot(snapshot(database))
    validate_export_bytes(raw)

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)

    descriptor = os.open(destination, flags, 0o600)

    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # Leave incomplete artifact in place; never silently overwrite it.
        raise
    finally:
        os.close(descriptor)

    # Flush directory metadata for crash durability where supported.
    directory_fd = os.open(
        destination.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

    return {
        "path": str(destination),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "policy_version": snapshot_version(raw),
    }


def snapshot_version(raw):
    return validate_export_bytes(raw)["policy_version"]
