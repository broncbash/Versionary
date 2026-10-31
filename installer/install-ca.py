#!/usr/bin/env python3
"""Safely install the public Versionary CA certificate."""

import argparse
import os
import stat
import sys
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID
from datetime import datetime, timezone


# CA trust is selected by the administrator, never by a developer's LAN.
EXPECTED_CA_SHA256 = None


def validate_ca(data, expected_sha256=None):
    if b"PRIVATE KEY" in data:
        raise ValueError("Private key material is forbidden")

    certificate = x509.load_pem_x509_certificate(data)

    constraints = certificate.extensions.get_extension_for_oid(
        ExtensionOID.BASIC_CONSTRAINTS
    ).value

    usage = certificate.extensions.get_extension_for_oid(
        ExtensionOID.KEY_USAGE
    ).value

    if not constraints.ca or not usage.key_cert_sign:
        raise ValueError("Certificate is not authorized as a CA")

    now = datetime.now(timezone.utc)

    # cryptography versions bundled with Debian 12 predate the
    # timezone-aware certificate validity properties.
    not_before = getattr(certificate, "not_valid_before_utc", None)
    not_after = getattr(certificate, "not_valid_after_utc", None)

    if not_before is None:
        not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)
    if not_after is None:
        not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)

    if not (not_before <= now < not_after):
        raise ValueError("CA certificate is outside its validity period")

    fingerprint = certificate.fingerprint(
        hashes.SHA256()
    ).hex()

    if expected_sha256 is not None and fingerprint != expected_sha256:
        raise ValueError(
            "CA fingerprint does not match trusted Versionary CA"
        )

    return fingerprint


def require_safe_existing_path(path, *, directory, expected_uid=0):
    """Reject unsafe ownership, permissions, and file types."""

    info = path.lstat()

    if stat.S_ISLNK(info.st_mode):
        raise ValueError("Symlinked CA installation path")

    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Invalid CA installation directory")
    else:
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Invalid CA certificate destination")
        if info.st_nlink != 1:
            raise ValueError("Hard-linked CA destination")

    if info.st_uid != expected_uid:
        raise ValueError("CA installation path has unsafe ownership")

    if info.st_mode & 0o022:
        raise ValueError("Unsafe CA installation path permissions")


def install_ca(source, root, expected_sha256=None):
    root = Path(root).absolute()
    source = Path(source)


    if not root.is_dir() or root.is_symlink():
        raise ValueError("Installation root must be a real directory")

    # A temporary test root may be writable by its owner,
    # but it must never be writable by other users.
    root_info = root.stat()

    # Production root requires root privileges.
    # Isolated roots are owned by the invoking user.
    if root == Path("/"):
        if os.geteuid() != 0:
            raise ValueError("Production installation requires root")
        expected_uid = 0
    else:
        expected_uid = os.geteuid()

    if root_info.st_uid != expected_uid:
        raise ValueError("Installation root has unsafe ownership")

    if root_info.st_mode & 0o022:
        raise ValueError("Unsafe installation root permissions")

    if source.is_symlink() or not source.is_file():
        raise ValueError("CA source must be a regular file")

    data = source.read_bytes()
    fingerprint = validate_ca(data, expected_sha256)

    destination_dir = root / "etc/versionary-agent"
    destination = destination_dir / "ca.crt"

    current = root

    for component in ("etc", "versionary-agent"):
        current = current / component

        if current.is_symlink():
            raise ValueError("Symlinked certificate directory")

        if current.exists():
            require_safe_existing_path(
                current,
                directory=True,
                expected_uid=expected_uid,
            )

    if destination.is_symlink():
        raise ValueError("Symlinked CA destination")

    if destination.exists():
        require_safe_existing_path(
            destination,
            directory=False,
            expected_uid=expected_uid,
        )

        existing = destination.read_bytes()

        if existing != data:
            raise ValueError(
                "Existing CA differs; refusing automatic replacement"
            )

        print("[OK] Existing trusted CA preserved")
        return fingerprint

    destination_dir.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=".ca-install-",
        dir=destination_dir,
    )

    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())

        os.chmod(temporary, 0o644)

        # Refuse to replace a CA created by another process.
        os.link(temporary, destination)
        os.unlink(temporary)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    print("[OK] Public CA certificate installed")
    return fingerprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--root", required=True)
    parser.add_argument("--sha256", help="Optional expected CA fingerprint")
    args = parser.parse_args()

    try:
        fingerprint = install_ca(args.source, args.root, args.sha256)
        print(f"[OK] CA SHA-256: {fingerprint}")
        return 0

    except (
        OSError,
        ValueError,
        x509.ExtensionNotFound,
    ) as exc:
        print(f"[ERROR] CA installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
