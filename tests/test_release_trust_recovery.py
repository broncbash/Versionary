"""Adversarial tests for existing-database authenticated recovery."""

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recovery = load(
    "release-trust-recovery.py", "versionary_recovery_tests"
)


class RecoveryTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "trust.db"
        self.authority_path = self.root / "authority.pem"
        self.policy_path = self.root / "policy.json"
        self.signature_path = self.root / "signature.json"

        self.authority = Ed25519PrivateKey.generate()
        self.authority_path.write_bytes(
            self.authority.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        release_key = Ed25519PrivateKey.generate().public_key()
        release_raw = release_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        release_pem = release_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        self.policy_path.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": [{
                "key_id": "sha256:" + hashlib.sha256(
                    release_raw
                ).hexdigest(),
                "public_key": release_pem,
                "status": "trusted",
            }],
        }))

        recovery.state.initialize(
            self.database, self.authority_path
        )
        self.sign(1)

    def sign(self, version):
        digest = hashlib.sha256(
            self.policy_path.read_bytes()
        ).hexdigest()
        signature = self.authority.sign(
            recovery.updates.signed_message(version, digest)
        )
        self.signature_path.write_text(json.dumps({
            "schema_version": 1,
            "algorithm": "Ed25519",
            "authority_key_id": recovery.updates.key_identity(
                self.authority.public_key()
            ),
            "policy_version": version,
            "policy_sha256": digest,
            "signature": base64.b64encode(signature).decode(),
        }))

    def apply(self, floor=0):
        return recovery.recover(
            self.database,
            self.authority_path,
            self.policy_path,
            self.signature_path,
            floor,
        )

    def version(self):
        return recovery.state.read_state(
            self.database
        )["policy_version"]

    def test_initial_authenticated_recovery(self):
        self.assertEqual(
            self.apply(1)["status"], "recovered"
        )
        self.assertEqual(self.version(), 1)

    def test_same_version_identical_is_noop(self):
        self.apply(1)
        self.assertEqual(
            self.apply(1)["status"], "unchanged"
        )

    def test_newer_version_accepted(self):
        self.apply(1)
        self.sign(2)
        self.assertEqual(
            self.apply(2)["policy_version"], 2
        )

    def test_older_version_rejected(self):
        self.apply(1)
        self.sign(2)
        self.apply(2)
        self.sign(1)
        with self.assertRaises(recovery.RecoveryError):
            self.apply(0)
        self.assertEqual(self.version(), 2)

    def test_minimum_version_enforced(self):
        with self.assertRaises(recovery.RecoveryError):
            self.apply(2)
        self.assertEqual(self.version(), 0)

    def test_invalid_signature_rejected(self):
        envelope = json.loads(
            self.signature_path.read_text()
        )
        envelope["signature"] = base64.b64encode(
            bytes(64)
        ).decode()
        self.signature_path.write_text(
            json.dumps(envelope)
        )
        with self.assertRaises(
            recovery.updates.PolicyUpdateError
        ):
            self.apply(1)
        self.assertEqual(self.version(), 0)

    def test_independent_authority_mismatch(self):
        other = Ed25519PrivateKey.generate().public_key()
        self.authority_path.write_bytes(
            other.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        with self.assertRaises(recovery.RecoveryError):
            self.apply(1)
        self.assertEqual(self.version(), 0)

    def test_conflicting_same_version_rejected(self):
        self.apply(1)
        original = self.policy_path.read_bytes()
        parsed = json.loads(original)
        parsed["keys"][0]["status"] = "revoked"
        self.policy_path.write_text(json.dumps(parsed))
        self.sign(1)
        with self.assertRaises(recovery.RecoveryError):
            self.apply(1)
        self.assertEqual(
            recovery.state.read_state(
                self.database
            )["policy_bytes"],
            original,
        )

    def test_missing_database_not_recreated(self):
        self.database.unlink()
        with self.assertRaises(
            recovery.state.TrustStateError
        ):
            self.apply(1)
        self.assertFalse(self.database.exists())

    def test_database_symlink_rejected(self):
        alias = self.root / "alias.db"
        alias.symlink_to(self.database)
        with self.assertRaises(
            recovery.state.TrustStateError
        ):
            recovery.recover(
                alias,
                self.authority_path,
                self.policy_path,
                self.signature_path,
                1,
            )

    def test_invalid_floor_type_rejected(self):
        for floor in (-1, True, "1"):
            with self.subTest(floor=floor):
                with self.assertRaises(
                    recovery.RecoveryError
                ):
                    self.apply(floor)

    def test_equivalent_authority_pem_format_accepted(self):
        from cryptography.hazmat.primitives import serialization

        alternate = self.authority.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )

        # OpenSSH is intentionally not accepted by the PEM-only
        # authority parser; the existing PEM format remains required.
        self.assertTrue(alternate.startswith(b"ssh-ed25519 "))

        self.assertEqual(
            self.apply(1)["status"],
            "recovered",
        )

    def test_cli_authenticated_recovery(self):
        result = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT / "installer/release-trust-admin.py"
                ),
                "recover",
                "--database", str(self.database),
                "--authority-public",
                str(self.authority_path),
                "--policy", str(self.policy_path),
                "--signature", str(self.signature_path),
                "--minimum-version", "1",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0, result.stderr
        )
        self.assertEqual(
            json.loads(result.stdout)["status"],
            "recovered",
        )


if __name__ == "__main__":
    unittest.main()
