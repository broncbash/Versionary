"""Integration tests for Versionary trust-policy enforcement."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


signing = load("release-signing.py", "versionary_policy_test_signing")
policy = load("release-trust-policy.py", "versionary_policy_test_policy")
trusted = load("verify-trusted-release.py", "versionary_policy_test_gate")


class PolicyIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.manifest = self.root / "manifest.json"
        self.signature = self.root / "manifest.sig.json"
        self.private = self.root / "private.pem"
        self.public = self.root / "public.pem"
        self.package = self.root / "versionary-agent.tar.gz"
        self.policy_path = self.root / "trust-policy.json"

        self.manifest.write_text('{"product":"Versionary"}')
        self.package.write_bytes(b"package")

        self.identity = signing.keygen(self.private, self.public)
        signing.sign(self.manifest, self.private, self.signature)

        self.provenance = Mock()
        self.provenance.verify.return_value = True

    def entry(self, public_path, status="trusted"):
        key = serialization.load_pem_public_key(
            public_path.read_bytes()
        )
        return {
            "key_id": policy.public_key_id(key),
            "public_key": public_path.read_text(),
            "status": status,
        }

    def write_policy(self, entries):
        self.policy_path.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": entries,
        }))

    def execute(self):
        original = trusted.load_tool

        def loader(name, module_name):
            if name == "verify-release-provenance.py":
                return self.provenance
            return original(name, module_name)

        with patch.object(trusted, "load_tool", side_effect=loader):
            return trusted.verify(
                manifest=self.manifest,
                signature=self.signature,
                package=self.package,
                trust_policy=self.policy_path,
            )

    def test_trusted_policy_success(self):
        self.write_policy([self.entry(self.public)])
        self.assertTrue(self.execute())
        self.provenance.verify.assert_called_once()

    def test_revoked_key_rejected_before_provenance(self):
        self.write_policy([self.entry(self.public, "revoked")])
        with self.assertRaisesRegex(
            trusted.TrustedReleaseError, "trust policy rejected"
        ):
            self.execute()
        self.provenance.verify.assert_not_called()

    def test_unknown_key_rejected_before_provenance(self):
        other_private = self.root / "other-private.pem"
        other_public = self.root / "other-public.pem"
        signing.keygen(other_private, other_public)
        self.write_policy([self.entry(other_public)])

        with self.assertRaises(trusted.TrustedReleaseError):
            self.execute()

        self.provenance.verify.assert_not_called()

    def test_two_trusted_keys_support_rotation(self):
        other_private = self.root / "other-private.pem"
        other_public = self.root / "other-public.pem"
        signing.keygen(other_private, other_public)

        self.write_policy([
            self.entry(other_public),
            self.entry(self.public),
        ])

        self.assertTrue(self.execute())

    def test_tampered_signature_rejected_before_provenance(self):
        self.write_policy([self.entry(self.public)])
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = "AAAA"
        self.signature.write_text(json.dumps(envelope))

        with self.assertRaises(trusted.TrustedReleaseError):
            self.execute()

        self.provenance.verify.assert_not_called()

    def test_duplicate_signature_fields_rejected(self):
        self.write_policy([self.entry(self.public)])
        self.signature.write_text(
            '{"key_id":"sha256:' + "a" * 64 + '",'
            '"key_id":"sha256:' + "b" * 64 + '"}'
        )

        with self.assertRaisesRegex(
            trusted.TrustedReleaseError, "Duplicate signature field"
        ):
            self.execute()

        self.provenance.verify.assert_not_called()

    def test_both_trust_modes_rejected(self):
        self.write_policy([self.entry(self.public)])

        with self.assertRaises(trusted.TrustedReleaseError):
            trusted.verify(
                manifest=self.manifest,
                signature=self.signature,
                trusted_public=self.public,
                package=self.package,
                trust_policy=self.policy_path,
            )

    def test_missing_trust_mode_rejected(self):
        with self.assertRaises(trusted.TrustedReleaseError):
            trusted.verify(
                manifest=self.manifest,
                signature=self.signature,
                package=self.package,
            )


if __name__ == "__main__":
    unittest.main()
