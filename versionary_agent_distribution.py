"""Opt-in, read-only Versionary agent distribution.

Distribution is disabled by default. Files are opened without following
symlinks and read from validated descriptors. No installation or signing
operations occur in this module.
"""

import hashlib
import os
import stat
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(
    prefix="/api/v1/distribution",
    tags=["Agent distribution"],
)

PACKAGE_NAME = "versionary-agent.tar.gz"
MANIFEST_NAME = "release-manifest.json"
SIGNATURE_NAME = "release-signature.json"

MAX_PACKAGE_BYTES = 100 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SIGNATURE_BYTES = 16 * 1024

ARTIFACTS = {
    PACKAGE_NAME: MAX_PACKAGE_BYTES,
    MANIFEST_NAME: MAX_MANIFEST_BYTES,
    SIGNATURE_NAME: MAX_SIGNATURE_BYTES,
}


def distribution_directory():
    if os.environ.get("VERSIONARY_DISTRIBUTION_ENABLED") != "true":
        raise HTTPException(404, "Agent distribution is disabled")

    configured = os.environ.get("VERSIONARY_DISTRIBUTION_DIR")
    if not configured:
        raise HTTPException(503, "Distribution directory is not configured")

    directory = Path(configured)
    if not directory.is_absolute():
        raise HTTPException(503, "Distribution directory must be absolute")

    return directory


def open_directory():
    directory = distribution_directory()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)

    try:
        fd = os.open(directory, flags)
        info = os.fstat(fd)

        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o002:
            raise ValueError("Unsafe distribution directory")

        return fd

    except (OSError, ValueError) as exc:
        if "fd" in locals():
            os.close(fd)
        raise HTTPException(503, "Distribution directory unavailable") from exc


def read_artifact(filename):
    if filename not in ARTIFACTS:
        raise HTTPException(503, "Unknown distribution artifact")

    directory_fd = open_directory()
    file_fd = None

    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW
        flags |= getattr(os, "O_CLOEXEC", 0)

        file_fd = os.open(
            filename,
            flags,
            dir_fd=directory_fd,
        )

        info = os.fstat(file_fd)
        limit = ARTIFACTS[filename]

        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Artifact is not a regular file")
        if info.st_mode & 0o002:
            raise ValueError("Artifact is world-writable")
        if not 0 < info.st_size <= limit:
            raise ValueError("Invalid artifact size")

        with os.fdopen(file_fd, "rb") as stream:
            file_fd = None
            data = stream.read(limit + 1)

        if not 0 < len(data) <= limit:
            raise ValueError("Invalid artifact content")

        return data

    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Distribution artifact unavailable") from exc

    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory_fd)


def package_path():
    """Compatibility helper for existing tests and callers."""
    directory = distribution_directory()
    read_artifact(PACKAGE_NAME)
    return directory / PACKAGE_NAME


def signed_release_file(filename, maximum):
    """Compatibility helper; validate through the hardened reader."""
    if ARTIFACTS.get(filename) != maximum:
        raise HTTPException(503, "Unsupported artifact")
    read_artifact(filename)
    return distribution_directory() / filename


def signed_release_ready():
    """Require the complete artifact set before serving signed metadata."""
    for name in (PACKAGE_NAME, MANIFEST_NAME, SIGNATURE_NAME):
        read_artifact(name)


@router.get("/agent/manifest")
def agent_manifest():
    package = read_artifact(PACKAGE_NAME)
    return {
        "product": "Versionary",
        "artifact": PACKAGE_NAME,
        "sha256": hashlib.sha256(package).hexdigest(),
        "download": "/api/v1/distribution/agent/package",
        "note": (
            "Checksum detects transfer errors. Independent package "
            "authentication is required before installation."
        ),
    }


@router.get("/agent/package")
def agent_package():
    package = read_artifact(PACKAGE_NAME)
    return Response(
        content=package,
        media_type="application/gzip",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'attachment; filename="versionary-agent.tar.gz"',
        },
    )


@router.get("/agent/release-manifest")
def release_manifest():
    signed_release_ready()
    return Response(
        content=read_artifact(MANIFEST_NAME),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/agent/release-signature")
def release_signature():
    signed_release_ready()
    return Response(
        content=read_artifact(SIGNATURE_NAME),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
