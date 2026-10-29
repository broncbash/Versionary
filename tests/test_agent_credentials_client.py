"""Tests for ARBY PATCH AGENT credential storage."""

import json
import tempfile
import unittest
from pathlib import Path

from agent.credentials import (
    CredentialError,
    load_credential,
    save_credential,
)


class TestAgentCredentialsClient(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "agent" / "credential.json"
        self.path.parent.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_save_and_load(self):
        save_credential("test-secret-token", self.path)

        self.assertEqual(
            load_credential(self.path),
            "test-secret-token",
        )

    def test_file_permissions(self):
        save_credential("test-secret-token", self.path)

        self.assertEqual(
            self.path.stat().st_mode & 0o777,
            0o600,
        )

    def test_missing_credential(self):
        with self.assertRaises(CredentialError):
            load_credential(self.path)

    def test_reject_empty_token(self):
        with self.assertRaises(CredentialError):
            save_credential("", self.path)

    def test_no_overwrite(self):
        save_credential("first-token", self.path)

        with self.assertRaises(CredentialError):
            save_credential("second-token", self.path)

        self.assertEqual(
            load_credential(self.path),
            "first-token",
        )

    def test_reject_insecure_permissions(self):
        save_credential("test-secret-token", self.path)
        self.path.chmod(0o644)

        with self.assertRaises(CredentialError):
            load_credential(self.path)

    def test_reject_corrupt_json(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{invalid json")
        self.path.chmod(0o600)

        with self.assertRaises(CredentialError):
            load_credential(self.path)

    def test_reject_missing_token_field(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"other": "value"}))
        self.path.chmod(0o600)

        with self.assertRaises(CredentialError):
            load_credential(self.path)

    def test_reject_symlink(self):
        save_credential(
            "test-secret-token",
            Path(self.temp.name) / "real.json",
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.symlink_to(
            Path(self.temp.name) / "real.json"
        )

        with self.assertRaises(CredentialError):
            load_credential(self.path)


if __name__ == "__main__":
    unittest.main()
