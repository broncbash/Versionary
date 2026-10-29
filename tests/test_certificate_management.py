import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone
from certificate_management import CertificateError, validate_pair, install_pair


def pair(host='example.test', expired=False):
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=10))
            .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=10))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
            .sign(key, hashes.SHA256()))
    return (cert.public_bytes(serialization.Encoding.PEM),
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


class CertificateManagementTests(unittest.TestCase):
    def test_valid(self):
        cert, key = pair()
        self.assertEqual(validate_pair(cert, key, 'example.test')['hostname'], 'example.test')

    def test_wrong_host(self):
        cert, key = pair()
        with self.assertRaisesRegex(CertificateError, 'SAN'):
            validate_pair(cert, key, 'wrong.test')

    def test_wrong_key(self):
        cert, _ = pair()
        _, key = pair()
        with self.assertRaisesRegex(CertificateError, 'match'):
            validate_pair(cert, key, 'example.test')

    def test_expired(self):
        cert, key = pair(expired=True)
        with self.assertRaisesRegex(CertificateError, 'valid'):
            validate_pair(cert, key, 'example.test')

    def test_install_preserves_existing(self):
        cert, key = pair()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'cert.pem').write_bytes(cert)
            (root / 'key.pem').write_bytes(key)
            dest = root / 'target'
            dest.mkdir(mode=0o700)
            install_pair(root / 'cert.pem', root / 'key.pem', 'example.test', dest)
            self.assertEqual((dest / 'server.key').stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(CertificateError, 'replace'):
                install_pair(root / 'cert.pem', root / 'key.pem', 'example.test', dest)

    def test_reject_public_destination(self):
        cert, key = pair()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'cert.pem').write_bytes(cert)
            (root / 'key.pem').write_bytes(key)
            dest = root / 'target'
            dest.mkdir(mode=0o755)
            with self.assertRaisesRegex(CertificateError, '0700'):
                install_pair(root / 'cert.pem', root / 'key.pem', 'example.test', dest)
