"""Development-only CLI and process-recovery tests."""

import base64
import hashlib
import importlib.util
import json
import os
import sqlite3
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
CLI = ROOT / "installer/release-trust-admin.py"
UPDATER = ROOT / "installer/release-policy-updates.py"

spec = importlib.util.spec_from_file_location(
    "versionary_admin_test_updater", UPDATER
)
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)


class TrustAdminTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / "trust.db"
        self.authority = Ed25519PrivateKey.generate()
        self.authority_path = self.root / "authority.pem"
        self.policy = self.root / "policy.json"
        self.signature = self.root / "signature.json"

        authority_public = self.authority.public_key()
        self.authority_path.write_bytes(
            authority_public.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        release_public = Ed25519PrivateKey.generate().public_key()
        release_pem = release_public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        release_raw = release_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        self.policy.write_text(json.dumps({
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

        self.sign(1)

    def sign(self, version):
        digest = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        signature = self.authority.sign(
            updates.signed_message(version, digest)
        )
        self.signature.write_text(json.dumps({
            "schema_version": 1,
            "algorithm": "Ed25519",
            "authority_key_id": updates.key_identity(
                self.authority.public_key()
            ),
            "policy_version": version,
            "policy_sha256": digest,
            "signature": base64.b64encode(signature).decode("ascii"),
        }))

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(CLI), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def bootstrap(self):
        return self.cli(
            "bootstrap",
            "--database", self.database,
            "--authority-public", self.authority_path,
        )

    def install(self):
        return self.cli(
            "install",
            "--database", self.database,
            "--policy", self.policy,
            "--signature", self.signature,
        )

    def inspect(self):
        return self.cli("inspect", "--database", self.database)

    def test_bootstrap_and_inspect(self):
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(self.inspect().stdout)
        self.assertEqual(record["policy_version"], 0)
        self.assertEqual(record["status"], "ok")

    def test_install_and_inspect(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(self.inspect().stdout)
        self.assertEqual(record["policy_version"], 1)
        self.assertEqual(record["status"], "ok")

    def test_rebootstrap_rejected(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        self.assertNotEqual(self.bootstrap().returncode, 0)
        self.assertEqual(
            json.loads(self.inspect().stdout)["policy_version"], 0
        )

    def test_replay_rejected(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        self.assertEqual(self.install().returncode, 0)
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(
            json.loads(self.inspect().stdout)["policy_version"], 1
        )

    def test_invalid_signature_does_not_advance_state(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = base64.b64encode(
            b"X" * 64
        ).decode("ascii")
        self.signature.write_text(json.dumps(envelope))
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(
            json.loads(self.inspect().stdout)["policy_version"], 0
        )

    def test_cli_does_not_expose_stored_public_key(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        result = self.inspect()
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(
            "BEGIN PUBLIC KEY", result.stdout
        )
        self.assertNotIn(
            "authority_public", result.stdout
        )

    def test_interrupted_process_rolls_back_transaction(self):
        """Abrupt process exit before COMMIT preserves previous state."""
        self.assertEqual(self.bootstrap().returncode, 0)

        code = """
import os
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    "UPDATE trust_state SET policy_version = 999 "
    "WHERE singleton = 1"
)
os._exit(17)
"""
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.database)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 17)
        inspected = self.inspect()
        self.assertEqual(
            inspected.returncode, 0, inspected.stderr
        )
        self.assertEqual(
            json.loads(inspected.stdout)["policy_version"], 0
        )

    def test_missing_database_rejected(self):
        self.assertNotEqual(self.inspect().returncode, 0)
        self.assertFalse(self.database.exists())

    def test_symlink_database_rejected(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        alias = self.root / "alias.db"
        alias.symlink_to(self.database)
        result = self.cli("inspect", "--database", alias)
        self.assertNotEqual(result.returncode, 0)

    def test_database_is_owner_only(self):
        self.assertEqual(self.bootstrap().returncode, 0)
        self.assertEqual(
            self.database.stat().st_mode & 0o777, 0o600
        )


if __name__ == "__main__":
    unittest.main()
