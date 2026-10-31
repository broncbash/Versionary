"""Regression tests for Versionary release trust policies."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/release-trust-policy.py"

spec = importlib.util.spec_from_file_location(
    "versionary_release_trust_policy_tests", SOURCE
)
trust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trust)


class TrustPolicyTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "trust-policy.json"

        self.key1 = Ed25519PrivateKey.generate().public_key()
        self.key2 = Ed25519PrivateKey.generate().public_key()

        self.entry1 = self.entry(self.key1)
        self.entry2 = self.entry(self.key2)

    def entry(self, key, status="trusted"):
        pem = key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return {
            "key_id": trust.public_key_id(key),
            "public_key": pem,
            "status": status,
        }

    def write(self, entries):
        self.path.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": entries,
        }))

    def test_single_trusted_key(self):
        self.write([self.entry1])
        self.assertEqual(
            trust.trusted_key(self.path, self.entry1["key_id"]),
            self.key1,
        )

    def test_rotation_with_two_trusted_keys(self):
        self.write([self.entry1, self.entry2])
        for entry in (self.entry1, self.entry2):
            self.assertEqual(
                trust.public_key_id(
                    trust.trusted_key(self.path, entry["key_id"])
                ),
                entry["key_id"],
            )

    def test_revoked_key_rejected(self):
        self.entry1["status"] = "revoked"
        self.write([self.entry1, self.entry2])
        with self.assertRaisesRegex(
            trust.TrustPolicyError, "revoked"
        ):
            trust.trusted_key(self.path, self.entry1["key_id"])

    def test_unknown_key_rejected(self):
        self.write([self.entry1])
        with self.assertRaisesRegex(
            trust.TrustPolicyError, "Unknown"
        ):
            trust.trusted_key(self.path, self.entry2["key_id"])

    def test_duplicate_key_rejected(self):
        self.write([self.entry1, self.entry1])
        with self.assertRaisesRegex(
            trust.TrustPolicyError, "Duplicate signing key"
        ):
            trust.load_policy(self.path)

    def test_fingerprint_mismatch_rejected(self):
        self.entry1["key_id"] = self.entry2["key_id"]
        self.write([self.entry1])
        with self.assertRaisesRegex(
            trust.TrustPolicyError, "fingerprint mismatch"
        ):
            trust.load_policy(self.path)

    def test_invalid_status_rejected(self):
        self.entry1["status"] = "maybe"
        self.write([self.entry1])
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(self.path)

    def test_boolean_schema_rejected(self):
        self.path.write_text(json.dumps({
            "schema_version": True,
            "product": "Versionary",
            "keys": [self.entry1],
        }))
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(self.path)

    def test_duplicate_json_fields_rejected(self):
        self.path.write_text(
            '{"schema_version":1,"schema_version":1,'
            '"product":"Versionary","keys":[]}'
        )
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(self.path)

    def test_symlink_policy_rejected(self):
        self.write([self.entry1])
        link = self.root / "policy-link.json"
        link.symlink_to(self.path)
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(link)

    def test_empty_policy_rejected(self):
        self.write([])
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(self.path)

    def test_unexpected_fields_rejected(self):
        self.path.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": [self.entry1],
            "trust_anyone": True,
        }))
        with self.assertRaises(trust.TrustPolicyError):
            trust.load_policy(self.path)


if __name__ == "__main__":
    unittest.main()
