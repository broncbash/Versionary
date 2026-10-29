"""Secure persistent Ed25519 identity keys for ARBY PATCH AGENT."""

import json
import os
import stat
from pathlib import Path

try:
    from .credentials import (
        CredentialError,
        prepare_directory,
        validate_directory,
    )
    from .enrollment_crypto import (
        generate_keypair,
        public_key_from_private,
    )
except ImportError:
    from credentials import (
        CredentialError,
        prepare_directory,
        validate_directory,
    )
    from enrollment_crypto import (
        generate_keypair,
        public_key_from_private,
    )


DEFAULT_KEY_PATH = Path(
    "/var/lib/arby-patch-agent/enrollment-key.json"
)


class EnrollmentKeyError(RuntimeError):
    """Enrollment key storage is missing, unsafe, or invalid."""


def load_keypair(path=DEFAULT_KEY_PATH):
    """Load a private key without following symlinks."""

    path = Path(path)

    try:
        validate_directory(path.parent)

        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path, flags)

        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())

            if not stat.S_ISREG(info.st_mode):
                raise EnrollmentKeyError(
                    "Enrollment key must be a regular file"
                )

            if info.st_uid != os.geteuid():
                raise EnrollmentKeyError(
                    "Enrollment key owner is incorrect"
                )

            if stat.S_IMODE(info.st_mode) != 0o600:
                raise EnrollmentKeyError(
                    "Enrollment key permissions must be 0600"
                )

            if info.st_size > 4096:
                raise EnrollmentKeyError(
                    "Enrollment key file is unexpectedly large"
                )

            data = json.load(stream)

    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError, CredentialError) as exc:
        raise EnrollmentKeyError(
            "Enrollment key storage is invalid"
        ) from exc

    if not isinstance(data, dict):
        raise EnrollmentKeyError("Invalid enrollment key format")

    if set(data) != {"private_key", "public_key"}:
        raise EnrollmentKeyError("Invalid enrollment key fields")

    private_key = data["private_key"]
    public_key = data["public_key"]

    try:
        derived_public = public_key_from_private(private_key)
    except (ValueError, TypeError) as exc:
        raise EnrollmentKeyError(
            "Invalid enrollment private key"
        ) from exc

    if public_key != derived_public:
        raise EnrollmentKeyError(
            "Enrollment public/private key mismatch"
        )

    return {
        "private_key": private_key,
        "public_key": public_key,
    }


def create_keypair(path=DEFAULT_KEY_PATH):
    """Create a new keypair exclusively; never overwrite existing keys."""

    path = Path(path)

    try:
        prepare_directory(path.parent)
    except (OSError, ValueError, CredentialError) as exc:
        raise EnrollmentKeyError(
            "Unsafe enrollment key directory"
        ) from exc

    private_key, public_key = generate_keypair()

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
    )

    fd = os.open(path, flags, 0o600)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(
                {
                    "private_key": private_key,
                    "public_key": public_key,
                },
                stream,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return {
        "private_key": private_key,
        "public_key": public_key,
    }


def get_or_create_keypair(path=DEFAULT_KEY_PATH):
    """Preserve an existing keypair across repeated installations."""

    existing = load_keypair(path)

    if existing is not None:
        return existing

    try:
        return create_keypair(path)
    except FileExistsError:
        # A concurrent process may have created the file.
        existing = load_keypair(path)
        if existing is None:
            raise EnrollmentKeyError(
                "Enrollment key disappeared during creation"
            )
        return existing
