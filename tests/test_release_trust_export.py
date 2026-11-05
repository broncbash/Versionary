"""Development-only trust-state export tests."""

import hashlib
import importlib.util
import json
import os
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

spec = importlib.util.spec_from_file_location(
    "versionary_test_export",
    ROOT / "installer/release-trust-export.py",
)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class TrustExportTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)
        self.database = self.root / "trust.db"
        self.destination = self.root / "backup.json"
        self.authority = self.root / "authority.pem"

        key = Ed25519PrivateKey.generate().public_key()
        self.authority.write_bytes(
            key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        export.state.initialize(self.database, self.authority)

    def test_export_creates_private_file(self):
        result = export.export_state(
            self.database, self.destination
        )
        self.assertEqual(result["policy_version"], 0)
        self.assertEqual(
            self.destination.stat().st_mode & 0o777, 0o600
        )

    def test_export_round_trip(self):
        export.export_state(self.database, self.destination)
        payload = export.validate_export_bytes(
            self.destination.read_bytes()
        )
        self.assertEqual(payload["policy_version"], 0)
        self.assertEqual(payload["product"], "Versionary")

    def test_existing_destination_not_overwritten(self):
        self.destination.write_text("KEEP")
        with self.assertRaises(FileExistsError):
            export.export_state(
                self.database, self.destination
            )
        self.assertEqual(self.destination.read_text(), "KEEP")

    def test_symlink_destination_not_followed(self):
        victim = self.root / "victim"
        victim.write_text("SAFE")
        self.destination.symlink_to(victim)

        with self.assertRaises(FileExistsError):
            export.export_state(
                self.database, self.destination
            )

        self.assertEqual(victim.read_text(), "SAFE")

    def test_public_directory_rejected(self):
        public = self.root / "public"
        public.mkdir(mode=0o755)

        with self.assertRaises(export.TrustExportError):
            export.export_state(
                self.database, public / "backup.json"
            )

    def test_relative_destination_rejected(self):
        with self.assertRaises(export.TrustExportError):
            export.export_state(
                self.database, Path("backup.json")
            )

    def test_corrupted_snapshot_rejected(self):
        export.export_state(self.database, self.destination)
        raw = bytearray(self.destination.read_bytes())
        raw[10] ^= 1

        with self.assertRaises(export.TrustExportError):
            export.validate_export_bytes(bytes(raw))

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(export.TrustExportError):
            export.validate_export_bytes(
                b'{"schema_version":1,"schema_version":1}'
            )

    def test_truncated_snapshot_rejected(self):
        export.export_state(self.database, self.destination)
        raw = self.destination.read_bytes()

        with self.assertRaises(export.TrustExportError):
            export.validate_export_bytes(raw[:len(raw) // 2])

    def test_oversized_snapshot_rejected(self):
        with self.assertRaises(export.TrustExportError):
            export.validate_export_bytes(
                b"X" * (export.MAX_EXPORT_BYTES + 1)
            )

    def test_missing_database_does_not_create_export(self):
        self.database.unlink()

        with self.assertRaises(Exception):
            export.export_state(
                self.database, self.destination
            )

        self.assertFalse(self.destination.exists())

    def test_symlink_database_rejected(self):
        alias = self.root / "database-alias.db"
        alias.symlink_to(self.database)

        with self.assertRaises(export.state.TrustStateError):
            export.export_state(alias, self.destination)

        self.assertFalse(self.destination.exists())

    def test_cli_export(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "installer/release-trust-admin.py"),
                "export",
                "--database", str(self.database),
                "--destination", str(self.destination),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record["status"], "exported")
        self.assertTrue(self.destination.is_file())


if __name__ == "__main__":
    unittest.main()
