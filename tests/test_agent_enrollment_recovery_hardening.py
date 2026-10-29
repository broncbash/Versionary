"""Tests for interrupted enrollment after credential installation."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from agent.credentials import load_credential, save_credential
from agent.enrollment_client import complete_v2, EnrollmentClientError
from agent.enrollment_crypto import (
    generate_keypair,
    hash_credential,
    sign_enrollment,
)
from agent.enrollment_journal import load_journal, save_journal
from enrollment_crypto import generate_challenge


class TestEnrollmentRecoveryHardening(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name) / "state"
        self.key = root / "key.json"
        self.journal = root / "journal.json"
        self.credential = root / "credential.json"

        self.identity = {
            "agent_id": str(uuid4()),
            "hostname": "recovery-test",
            "platform": "arch",
        }

        from agent.enrollment_keys import get_or_create_keypair
        keys = get_or_create_keypair(self.key)

        self.token = "test-recovery-token"
        challenge = generate_challenge()
        credential_hash = hash_credential(self.token)

        save_journal({
            "agent_id": self.identity["agent_id"],
            "challenge": challenge,
            "signature": sign_enrollment(
                keys["private_key"],
                self.identity["agent_id"],
                challenge,
                credential_hash,
            ),
            "credential_hash": credential_hash,
            "token": self.token,
        }, self.journal)

        save_credential(self.token, self.credential)

    def kwargs(self):
        return {
            "key_path": self.key,
            "journal_path": self.journal,
            "credential_path": self.credential,
        }

    def test_confirmed_recovery(self):
        def fake_post(path, payload):
            self.assertTrue(path.endswith("/complete"))
            return {
                "agent_id": self.identity["agent_id"],
                "status": "enrolled",
                "recovered": True,
            }

        result = complete_v2(
            self.identity,
            post=fake_post,
            **self.kwargs(),
        )

        self.assertTrue(result["recovered"])
        self.assertIsNone(load_journal(self.journal))
        self.assertEqual(load_credential(self.credential), self.token)

    def test_failed_recovery_preserves_state(self):
        def unavailable(path, payload):
            raise ConnectionError("Server unavailable")

        with self.assertRaises(ConnectionError):
            complete_v2(
                self.identity,
                post=unavailable,
                **self.kwargs(),
            )

        self.assertIsNotNone(load_journal(self.journal))
        self.assertEqual(load_credential(self.credential), self.token)

    def test_invalid_confirmation_preserves_state(self):
        def fake_post(path, payload):
            return {
                "agent_id": self.identity["agent_id"],
                "status": "pending",
                "recovered": False,
            }

        with self.assertRaises(EnrollmentClientError):
            complete_v2(
                self.identity,
                post=fake_post,
                **self.kwargs(),
            )

        self.assertIsNotNone(load_journal(self.journal))
        self.assertEqual(load_credential(self.credential), self.token)


if __name__ == "__main__":
    unittest.main()
