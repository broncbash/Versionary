"""Offline TLS certificate validation and non-destructive installation.

No private key is ever returned by the API. This module does not reload a proxy.
"""
from __future__ import annotations

import ipaddress
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519, ed448, padding
from cryptography.x509.oid import ExtendedKeyUsageOID


class CertificateError(ValueError):
    pass


def _read_regular(path: Path, max_bytes: int = 128 * 1024) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                raise CertificateError('Expected a regular certificate file within size limit')
            data = os.read(fd, max_bytes + 1)
            if len(data) > max_bytes:
                raise CertificateError('Certificate file too large')
            return data
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        raise CertificateError('Cannot safely read certificate input') from exc


def validate_pair(cert_pem: bytes, key_pem: bytes, hostname: str) -> dict:
    """Validate leaf TLS cert, private key, expiry, and exact requested DNS/IP SAN."""
    if not hostname or not isinstance(hostname, str):
        raise CertificateError('Hostname is required')
    try:
        cert = x509.load_pem_x509_certificate(cert_pem)
        key = serialization.load_pem_private_key(key_pem, password=None)
    except (ValueError, TypeError) as exc:
        raise CertificateError('Invalid PEM certificate or unencrypted private key') from exc
    if cert.public_key() != key.public_key():
        raise CertificateError('Certificate and private key do not match')
    now = datetime.now(timezone.utc)
    if cert.not_valid_before_utc > now or cert.not_valid_after_utc <= now:
        raise CertificateError('Certificate is not currently valid')
    try:
        if cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise CertificateError('CA certificate cannot be used as a server certificate')
    except x509.ExtensionNotFound:
        pass
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
            raise CertificateError('Certificate is not valid for server authentication')
    except x509.ExtensionNotFound:
        pass
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound as exc:
        raise CertificateError('Server certificate must include a SAN') from exc
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        matched = hostname.lower().rstrip('.') in [name.lower().rstrip('.') for name in san.get_values_for_type(x509.DNSName)]
    else:
        matched = address in san.get_values_for_type(x509.IPAddress)
    if not matched:
        raise CertificateError('Certificate SAN does not match configured hostname/IP')
    return {'hostname': hostname, 'not_after': cert.not_valid_after_utc.isoformat(),
            'sha256': cert.fingerprint(hashes.SHA256()).hex(), 'subject': cert.subject.rfc4514_string()}


def validate_files(cert_file: str | Path, key_file: str | Path, hostname: str) -> dict:
    return validate_pair(_read_regular(Path(cert_file)), _read_regular(Path(key_file)), hostname)


def install_pair(cert_file: str | Path, key_file: str | Path, hostname: str, destination: str | Path) -> dict:
    """Install a validated pair only to an empty, private directory.

    Existing certs are never overwritten. No service is restarted or enabled.
    """
    cert_data = _read_regular(Path(cert_file))
    key_data = _read_regular(Path(key_file))
    info = validate_pair(cert_data, key_data, hostname)
    destination = Path(destination)
    if destination.is_symlink() or not destination.is_dir():
        raise CertificateError('Destination must be an existing private directory')
    st = destination.stat()
    if st.st_mode & 0o077:
        raise CertificateError('Destination must have mode 0700')
    names = ('server.crt', 'server.key')
    if any((destination / name).exists() or (destination / name).is_symlink() for name in names):
        raise CertificateError('Refusing to replace existing certificate material')
    written = []
    try:
        for name, data, mode in (('server.crt', cert_data, 0o600), ('server.key', key_data, 0o600)):
            fd = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
            written.append(destination / name)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return info
