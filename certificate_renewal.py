"""Offline server leaf renewal with an existing local CA; no live reload.

Writes a new, non-overwriting certificate/key pair into a private directory.
The caller must explicitly configure a TLS terminator to use the new pair.
"""
import ipaddress
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from certificate_management import validate_files


class RenewalError(ValueError):
    pass


def _read_regular(path, private=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 128 * 1024 or (private and info.st_mode & 0o077):
            raise RenewalError('Expected regular file with private permissions')
        data = os.read(fd, 128 * 1024 + 1)
        if len(data) > 128 * 1024:
            raise RenewalError('Issuer file too large')
        return data
    finally:
        os.close(fd)


def renew(ca_cert_path, ca_key_path, hostname, output, days=365):
    if type(days) is not int or not 1 <= days <= 825:
        raise RenewalError('Validity must be between 1 and 825 days')
    if not hostname or any(c in hostname for c in '/\\\x00') or len(hostname) > 253:
        raise RenewalError('Invalid hostname')
    try:
        san = x509.IPAddress(ipaddress.ip_address(hostname))
    except ValueError:
        labels = hostname.split('.')
        if not all(x and len(x) <= 63 and x[0].isalnum() and x[-1].isalnum() and
                   all(c.isascii() and (c.isalnum() or c == '-') for c in x) for x in labels):
            raise RenewalError('Invalid DNS hostname')
        san = x509.DNSName(hostname)
    ca = x509.load_pem_x509_certificate(_read_regular(ca_cert_path))
    key = serialization.load_pem_private_key(_read_regular(ca_key_path, private=True), password=None)
    if ca.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo) != key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
        raise RenewalError('CA certificate and key do not match')
    try:
        if not ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise RenewalError('Issuer is not a CA')
        usage = ca.extensions.get_extension_for_class(x509.KeyUsage).value
        if not usage.key_cert_sign:
            raise RenewalError('Issuer cannot sign certificates')
    except x509.ExtensionNotFound as exc:
        raise RenewalError('Issuer lacks required CA extensions') from exc
    now = datetime.now(timezone.utc)
    if ca.not_valid_before_utc > now or ca.not_valid_after_utc <= now + timedelta(days=days):
        raise RenewalError('CA validity does not cover requested leaf lifetime')
    output = Path(output)
    if output.is_symlink() or not output.is_dir() or output.stat().st_mode & 0o077:
        raise RenewalError('Existing private output directory (0700) required')
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)]))
        .issuer_name(ca.subject).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([san]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256()))
    files = {'server.key': leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
             'server.crt': leaf.public_bytes(serialization.Encoding.PEM)}
    created = []
    try:
        for name, content in files.items():
            path = output / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600 if name.endswith('.key') else 0o644)
            created.append(path)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        validate_files(output / 'server.crt', output / 'server.key', hostname)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {'certificate': str(output / 'server.crt'), 'key': str(output / 'server.key'), 'applied': False}
