"""Tests for authenticated Versionary trust-policy update validation."""

import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/release-policy-updates.py"

spec = importlib.util.spec_from_file_location(
    "versionary_policy_update_tests", SOURCE
)
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)


class PolicyUpdateTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.authority = Ed25519PrivateKey.generate()
        self.authority_public = self.root / "authority.pem"
        self.authority_public.write_bytes(
            self.authority.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        self.release_key = Ed25519PrivateKey.generate().public_key()
        release_pem = self.release_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

        release_raw = self.release_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        self.policy = self.root / "policy.json"
        self.policy.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": [{
                "key_id": "sha256:" + hashlib.sha256(release_raw).hexdigest(),
                "public_key": release_pem,
                "status": "trusted",
            }],
        }))

        self.signature = self.root / "policy.sig.json"
        self.sign(version=2)

    def sign(self, version=2, authority=None):
        authority = authority or self.authority
        digest = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        signature = authority.sign(
            updates.signed_message(version, digest)
        )
        self.signature.write_text(json.dumps({
            "schema_version": 1,
            "algorithm": "Ed25519",
            "authority_key_id": updates.key_identity(
                authority.public_key()
            ),
            "policy_version": version,
            "policy_sha256": digest,
            "signature": base64.b64encode(signature).decode("ascii"),
        }))

    def verify(self, current=1):
        return updates.verify_update(
            self.policy,
            self.signature,
            self.authority_public,
            current,
        )

    def test_valid_authenticated_update(self):
        self.assertEqual(self.verify(), 2)

    def test_bootstrap_version_zero_accepted(self):
        self.assertEqual(self.verify(current=0), 2)

    def test_signed_policy_version_zero_rejected(self):
        with self.assertRaises(updates.PolicyUpdateError):
            updates.signed_message(0, "0" * 64)

    def test_replay_rejected(self):
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "rollback or replay"
        ):
            self.verify(current=2)

    def test_rollback_rejected(self):
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "rollback or replay"
        ):
            self.verify(current=3)

    def test_tampered_policy_rejected(self):
        self.policy.write_bytes(self.policy.read_bytes() + b"\n")
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "digest mismatch"
        ):
            self.verify()

    def test_untrusted_authority_rejected(self):
        self.sign(authority=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "Untrusted policy authority"
        ):
            self.verify()

    def test_invalid_signature_rejected(self):
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = base64.b64encode(b"\0" * 64).decode()
        self.signature.write_text(json.dumps(envelope))
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "signature verification failed"
        ):
            self.verify()

    def test_boolean_version_rejected(self):
        with self.assertRaises(updates.PolicyUpdateError):
            self.verify(current=True)

    def test_duplicate_json_field_rejected(self):
        self.signature.write_text(
            '{"schema_version":1,"schema_version":1}'
        )
        with self.assertRaises(updates.PolicyUpdateError):
            self.verify()

    def test_invalid_policy_rejected(self):
        self.policy.write_text('{"product":"Versionary"}')
        self.sign()
        with self.assertRaises(Exception):
            self.verify()

    def test_wrong_authority_key_rejected(self):
        other = Ed25519PrivateKey.generate()
        self.authority_public.write_bytes(
            other.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "Untrusted policy authority"
        ):
            self.verify()


if __name__ == "__main__":
    unittest.main()
