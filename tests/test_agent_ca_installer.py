"""Security regression tests for the agent CA installer."""

import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/install-ca.py"
TRUSTED_CA = None

spec = importlib.util.spec_from_file_location(
    "arby_ca_installer_tests", SCRIPT
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def create_untrusted_ca():
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)

    name = x509.Name([
        x509.NameAttribute(
            NameOID.COMMON_NAME, "ARBY Test Untrusted CA"
        )
    ])

    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
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
    )

    return certificate.public_bytes(
        serialization.Encoding.PEM
    )


class TestAgentCAInstaller(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="arby-ca-unit-"
        )
        self.root = Path(self.temp.name)
        self.trusted_ca = self.root / "trusted-ca.crt"
        self.trusted_ca.write_bytes(create_untrusted_ca())

    def tearDown(self):
        self.temp.cleanup()

    def test_trusted_ca_accepted(self):
        fingerprint = installer.install_ca(
            self.trusted_ca, self.root
        )

        self.assertEqual(
            fingerprint,
            installer.validate_ca(self.trusted_ca.read_bytes()),
        )

        destination = (
            self.root / "etc/arby-patch-agent/ca.crt"
        )

        self.assertEqual(
            destination.read_bytes(),
            self.trusted_ca.read_bytes(),
        )

    def test_different_valid_ca_rejected(self):
        with self.assertRaisesRegex(
            ValueError, "fingerprint"
        ):
            installer.validate_ca(create_untrusted_ca(), expected_sha256="0" * 64)

    def test_reinstallation_preserves_ca(self):
        installer.install_ca(self.trusted_ca, self.root)

        destination = (
            self.root / "etc/arby-patch-agent/ca.crt"
        )

        before = destination.read_bytes()

        installer.install_ca(self.trusted_ca, self.root)

        self.assertEqual(destination.read_bytes(), before)

    def test_symlink_destination_rejected(self):
        destination_dir = (
            self.root / "etc/arby-patch-agent"
        )
        destination_dir.mkdir(parents=True)

        outside = self.root / "outside.crt"
        outside.write_text("DO NOT TOUCH")

        destination = destination_dir / "ca.crt"
        destination.symlink_to(outside)

        with self.assertRaisesRegex(
            ValueError, "Symlinked"
        ):
            installer.install_ca(self.trusted_ca, self.root)

        self.assertEqual(
            outside.read_text(), "DO NOT TOUCH"
        )

    def test_conflicting_valid_ca_preserves_existing_trust(self):
        installer.install_ca(self.trusted_ca, self.root)
        destination = self.root / "etc/arby-patch-agent/ca.crt"
        before = destination.read_bytes()
        replacement = self.root / "replacement-ca.crt"
        replacement.write_bytes(create_untrusted_ca())
        with self.assertRaises(ValueError):
            installer.install_ca(replacement, self.root)
        self.assertEqual(destination.read_bytes(), before)

    def test_mismatched_expected_fingerprint_preserves_existing_trust(self):
        installer.install_ca(self.trusted_ca, self.root)
        destination = self.root / "etc/arby-patch-agent/ca.crt"
        before = destination.read_bytes()
        with self.assertRaises(ValueError):
            installer.install_ca(self.trusted_ca, self.root,
                                 expected_sha256="0" * 64)
        self.assertEqual(destination.read_bytes(), before)

    def test_hardlinked_ca_destination_rejected_without_mutation(self):
        import os
        installer.install_ca(self.trusted_ca, self.root)
        destination = self.root / "etc/arby-patch-agent/ca.crt"
        before = destination.read_bytes()
        os.link(destination, self.root / "linked-ca.crt")
        with self.assertRaises(ValueError):
            installer.install_ca(self.trusted_ca, self.root)
        self.assertEqual(destination.read_bytes(), before)

    def test_private_key_material_rejected(self):
        data = (
            self.trusted_ca.read_bytes()
            + b"\n-----BEGIN PRIVATE KEY-----\n"
            + b"TEST\n-----END PRIVATE KEY-----\n"
        )

        with self.assertRaisesRegex(
            ValueError, "Private key"
        ):
            installer.validate_ca(data)


if __name__ == "__main__":
    unittest.main()
