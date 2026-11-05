"""Secure credential storage for VERSIONARY AGENT."""

import json
import os
import stat
from pathlib import Path


DEFAULT_CREDENTIAL_PATH = Path(
    "/var/lib/versionary-agent/credential.json"
)


class CredentialError(RuntimeError):
    """Agent credential is missing or invalid."""


def validate_token(token):
    if (
        not isinstance(token, str)
        or not token
        or len(token) > 4096
        or any(char.isspace() or ord(char) < 33
               or ord(char) == 127 for char in token)
    ):
        raise CredentialError("Invalid agent credential token")

    return token


def validate_directory(directory):
    """Require a private directory with no symlinked ancestors."""

    directory = Path(directory).absolute()

    for component in reversed((directory, *directory.parents)):
        info = component.lstat()

        if stat.S_ISLNK(info.st_mode):
            raise CredentialError(
                "Symlinked credential directory path is forbidden"
            )

    info = directory.lstat()

    if not stat.S_ISDIR(info.st_mode):
        raise CredentialError("Credential directory is not a directory")

    if info.st_uid != os.geteuid():
        raise CredentialError("Credential directory owner is incorrect")

    if stat.S_IMODE(info.st_mode) != 0o700:
        raise CredentialError(
            "Credential directory permissions must be 0700"
        )


def prepare_directory(directory):
    """Create the private credential directory if necessary."""

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    validate_directory(directory)


def load_credential(path=DEFAULT_CREDENTIAL_PATH):
    """Read a credential without following the final symlink."""

    path = Path(path)

    try:
        validate_directory(path.parent)

        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path, flags)

        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())

            if not stat.S_ISREG(info.st_mode):
                raise CredentialError(
                    "Credential must be a regular file"
                )

            if info.st_uid != os.geteuid():
                raise CredentialError(
                    "Credential file owner is incorrect"
                )

            if stat.S_IMODE(info.st_mode) != 0o600:
                raise CredentialError(
                    "Credential file permissions must be 0600"
                )

            if info.st_size > 8192:
                raise CredentialError(
                    "Credential file is unexpectedly large"
                )

            data = json.load(stream)

    except FileNotFoundError as exc:
        raise CredentialError(
            "Agent credential has not been provisioned"
        ) from exc

    except (OSError, ValueError, TypeError) as exc:
        raise CredentialError(
            "Agent credential file is invalid"
        ) from exc

    if not isinstance(data, dict):
        raise CredentialError("Invalid credential format")

    return validate_token(data.get("token"))


def save_credential(
    token,
    path=DEFAULT_CREDENTIAL_PATH,
):
    """Create a private credential without replacing existing data."""

    validate_token(token)

    path = Path(path)
    prepare_directory(path.parent)

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
    )

    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise CredentialError(
            "Credential already exists; refusing overwrite"
        ) from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"token": token}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
