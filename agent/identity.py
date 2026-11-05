"""Persistent identity for VERSIONARY AGENT."""

import json
import os
from pathlib import Path
import uuid


DEFAULT_IDENTITY_PATH = Path(
    "/var/lib/versionary-agent/identity.json"
)


def load_identity(path=DEFAULT_IDENTITY_PATH):
    """Load an existing agent identity, or return None."""

    path = Path(path)

    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))

    agent_id = str(uuid.UUID(data["agent_id"]))
    hostname = data["hostname"]
    platform = data["platform"]

    if not isinstance(hostname, str) or not hostname:
        raise ValueError("Invalid agent hostname")

    if not isinstance(platform, str) or not platform:
        raise ValueError("Invalid agent platform")

    return {
        "agent_id": agent_id,
        "hostname": hostname,
        "platform": platform,
    }


def create_identity(hostname, platform, path=DEFAULT_IDENTITY_PATH):
    """Create an identity once; never silently replace one."""

    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    identity = {
        "agent_id": str(uuid.uuid4()),
        "hostname": hostname,
        "platform": platform,
    }

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

    fd = os.open(path, flags, 0o600)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(identity, stream, indent=2)
            stream.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return identity


def get_or_create_identity(
    hostname,
    platform,
    path=DEFAULT_IDENTITY_PATH,
):
    """Return the persistent identity for this installation."""

    existing = load_identity(path)

    if existing is not None:
        return existing

    try:
        return create_identity(hostname, platform, path)
    except FileExistsError:
        # Another process may have created the identity.
        return load_identity(path)
