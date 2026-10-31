"""CA validation compatibility with older cryptography releases."""

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "versionary_ca_legacy", ROOT / "installer/install-ca.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_ca(not_before, not_after):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Disposable compatibility CA")
    ])
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
    )


class LegacyCertificate:
    """Expose only the older naive-UTC validity properties."""

    def __init__(self, certificate):
        self._certificate = certificate

    @property
    def extensions(self):
        return self._certificate.extensions

    @property
    def not_valid_before(self):
        return self._certificate.not_valid_before

    @property
    def not_valid_after(self):
        return self._certificate.not_valid_after

    def fingerprint(self, algorithm):
        return self._certificate.fingerprint(algorithm)


class LegacyCACompatibilityTests(unittest.TestCase):
    def validate_as_legacy(self, pem):
        original = x509.load_pem_x509_certificate
        certificate = original(pem)
        with patch.object(
            MODULE.x509,
            "load_pem_x509_certificate",
            return_value=LegacyCertificate(certificate),
        ):
            return MODULE.validate_ca(pem)

    def test_valid_legacy_certificate_accepted(self):
        now = datetime.now(timezone.utc)
        pem = make_ca(now - timedelta(days=1), now + timedelta(days=1))
        self.assertEqual(len(self.validate_as_legacy(pem)), 64)

    def test_expired_legacy_certificate_rejected(self):
        now = datetime.now(timezone.utc)
        pem = make_ca(now - timedelta(days=3), now - timedelta(days=1))
        with self.assertRaisesRegex(ValueError, "validity period"):
            self.validate_as_legacy(pem)

    def test_future_legacy_certificate_rejected(self):
        now = datetime.now(timezone.utc)
        pem = make_ca(now + timedelta(days=1), now + timedelta(days=3))
        with self.assertRaisesRegex(ValueError, "validity period"):
            self.validate_as_legacy(pem)


if __name__ == "__main__":
    unittest.main()
