"""Tests for atomic enrollment completion."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import agent_registry
import enrollment_store
from enrollment_completion import (
    complete_enrollment,
    EnrollmentCompletionError,
)
from enrollment_crypto import (
    generate_keypair,
    generate_challenge,
    sign_challenge,
)
from enrollment_v2 import register_with_key


class TestEnrollmentCompletion(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.db_path = Path(self.temp.name) / "agents.db"

        patcher = patch.object(
            agent_registry, "DB_PATH", self.db_path
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        agent_registry.initialize_database()

        self.private_key, public_key = generate_keypair()
        self.agent_id = str(uuid4())

        register_with_key(
            self.agent_id,
            "test-node",
            "arch",
            public_key,
        )

        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )

        self.challenge = enrollment_store.create_challenge(
            self.agent_id
        )

    def complete(self, challenge=None, signature=None):
        challenge = (
            self.challenge if challenge is None else challenge
        )
        signature = (
            sign_challenge(self.private_key, challenge)
            if signature is None else signature
        )
        return complete_enrollment(
            self.agent_id, challenge, signature
        )

    def credential_count(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return db.execute(
                """
                SELECT COUNT(*)
                FROM agent_credentials
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()[0]

    def test_valid_enrollment(self):
        result = self.complete()

        self.assertEqual(result["status"], "enrolled")
        self.assertTrue(
            agent_registry.authenticate_agent(
                self.agent_id, result["token"]
            )
        )
        self.assertEqual(self.credential_count(), 1)

    def test_replay_rejected(self):
        self.complete()

        with self.assertRaises(EnrollmentCompletionError):
            self.complete()

        self.assertEqual(self.credential_count(), 1)

    def test_wrong_private_key_rejected(self):
        other_private, _ = generate_keypair()
        signature = sign_challenge(
            other_private, self.challenge
        )

        with self.assertRaises(EnrollmentCompletionError):
            self.complete(signature=signature)

        self.assertEqual(self.credential_count(), 0)

    def test_wrong_challenge_rejected(self):
        with self.assertRaises(EnrollmentCompletionError):
            self.complete(challenge=generate_challenge())

        self.assertEqual(self.credential_count(), 0)

    def test_expired_challenge_rejected(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            with db:
                db.execute(
                    """
                    UPDATE agent_enrollments
                    SET challenge_expires =
                        '2000-01-01T00:00:00+00:00'
                    WHERE agent_id = ?
                    """,
                    (self.agent_id,),
                )

        with self.assertRaises(EnrollmentCompletionError):
            self.complete()

        self.assertEqual(self.credential_count(), 0)

    def test_revoked_agent_rejected(self):
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )

        with self.assertRaises(EnrollmentCompletionError):
            self.complete()

        self.assertEqual(self.credential_count(), 0)

    def test_invalid_signature_preserves_challenge(self):
        with self.assertRaises(EnrollmentCompletionError):
            self.complete(signature="invalid")

        self.assertIsNotNone(
            enrollment_store.get_active_challenge(
                self.agent_id
            )
        )

    def test_success_consumes_challenge(self):
        self.complete()

        self.assertIsNone(
            enrollment_store.get_active_challenge(
                self.agent_id
            )
        )

    def test_token_not_stored_in_plaintext(self):
        result = self.complete()

        with closing(sqlite3.connect(self.db_path)) as db:
            stored = db.execute(
                """
                SELECT token_hash
                FROM agent_credentials
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()[0]

        self.assertNotEqual(stored, result["token"])


if __name__ == "__main__":
    unittest.main()
