"""Crash-recovery journal for VERSIONARY AGENT enrollment v2."""

import json
import os
import stat
from pathlib import Path

from .credentials import (
    CredentialError,
    prepare_directory,
    validate_directory,
    validate_token,
)
from .enrollment_crypto import (
    decode_bytes,
    EnrollmentCryptoError,
)


DEFAULT_JOURNAL_PATH = Path(
    "/var/lib/versionary-agent/enrollment-pending.json"
)


class EnrollmentJournalError(RuntimeError):
    """Enrollment journal is missing, unsafe, or invalid."""


def validate_entry(entry):
    if not isinstance(entry, dict):
        raise EnrollmentJournalError("Invalid enrollment journal")

    required = {
        "agent_id",
        "challenge",
        "signature",
        "credential_hash",
        "token",
    }

    if set(entry) != required:
        raise EnrollmentJournalError(
            "Invalid enrollment journal fields"
        )

    try:
        from uuid import UUID
        import hashlib
        import re

        agent_id = entry["agent_id"]

        if (
            not isinstance(agent_id, str)
            or str(UUID(agent_id)) != agent_id
        ):
            raise ValueError("Invalid agent ID")

        decode_bytes(entry["challenge"], 32)
        decode_bytes(entry["signature"], 64)
        validate_token(entry["token"])

        expected_hash = hashlib.sha256(
            entry["token"].encode("utf-8")
        ).hexdigest()

        if (
            not isinstance(entry["credential_hash"], str)
            or not re.fullmatch(
                r"[0-9a-f]{64}",
                entry["credential_hash"],
            )
            or entry["credential_hash"] != expected_hash
        ):
            raise ValueError("Credential hash mismatch")

    except (
        ValueError,
        TypeError,
        KeyError,
        CredentialError,
        EnrollmentCryptoError,
    ) as exc:
        raise EnrollmentJournalError(
            "Invalid enrollment journal contents"
        ) from exc

    return entry


def load_journal(path=DEFAULT_JOURNAL_PATH):
    """Read a journal without following symlinks."""

    path = Path(path)

    try:
        validate_directory(path.parent)

        fd = os.open(
            path,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
        )

        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())

            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > 8192
            ):
                raise EnrollmentJournalError(
                    "Unsafe enrollment journal file"
                )

            entry = json.load(stream)

    except FileNotFoundError:
        return None
    except (
        OSError,
        ValueError,
        TypeError,
        CredentialError,
    ) as exc:
        raise EnrollmentJournalError(
            "Cannot securely load enrollment journal"
        ) from exc

    return validate_entry(entry)


def save_journal(entry, path=DEFAULT_JOURNAL_PATH):
    """Persist a journal exclusively before contacting the server."""

    validate_entry(entry)
    path = Path(path)

    try:
        prepare_directory(path.parent)
    except (OSError, CredentialError) as exc:
        raise EnrollmentJournalError(
            "Unsafe enrollment journal directory"
        ) from exc

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(entry, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return entry


def delete_journal(path=DEFAULT_JOURNAL_PATH):
    """Remove only a verified private journal."""

    path = Path(path)

    entry = load_journal(path)

    if entry is None:
        return False

    path.unlink()
    return True
