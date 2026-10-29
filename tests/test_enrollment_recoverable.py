"""Security tests for recoverable, credential-bound enrollment."""

import hashlib
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import agent_registry
import enrollment_store
from enrollment_crypto import generate_keypair, generate_challenge
from enrollment_recoverable import (
    complete_recoverable_enrollment,
    sign_enrollment,
    RecoverableEnrollmentError,
)
from enrollment_v2 import register_with_key


class TestRecoverableEnrollment(unittest.TestCase):

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
            self.agent_id, "test-node", "arch", public_key
        )
        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )

        self.challenge = enrollment_store.create_challenge(
            self.agent_id
        )

        self.token = secrets.token_urlsafe(48)
        self.token_hash = hashlib.sha256(
            self.token.encode()
        ).hexdigest()

    def complete(self, **overrides):
        values = {
            "agent_id": self.agent_id,
            "challenge": self.challenge,
            "credential_hash": self.token_hash,
        }
        values.update(overrides)

        signature = values.pop(
            "signature",
            sign_enrollment(
                self.private_key,
                values["agent_id"],
                values["challenge"],
                values["credential_hash"],
            ),
        )
        return complete_recoverable_enrollment(
            signature=signature, **values
        )

    def credential_count(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return db.execute(
                "SELECT COUNT(*) FROM agent_credentials"
            ).fetchone()[0]

    def test_success(self):
        result = self.complete()
        self.assertFalse(result["recovered"])
        self.assertTrue(
            agent_registry.authenticate_agent(
                self.agent_id, self.token
            )
        )

    def test_lost_response_retry(self):
        self.complete()
        self.assertTrue(self.complete()["recovered"])
        self.assertEqual(self.credential_count(), 1)

    def test_wrong_credential_hash_rejected(self):
        self.complete()
        other_hash = hashlib.sha256(b"other").hexdigest()

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete(credential_hash=other_hash)

        self.assertEqual(self.credential_count(), 1)

    def test_signature_cannot_authorize_different_hash(self):
        signature = sign_enrollment(
            self.private_key,
            self.agent_id,
            self.challenge,
            self.token_hash,
        )
        other_hash = hashlib.sha256(b"other").hexdigest()

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete(
                credential_hash=other_hash,
                signature=signature,
            )

        self.assertEqual(self.credential_count(), 0)

    def test_wrong_private_key(self):
        other_private, _ = generate_keypair()
        signature = sign_enrollment(
            other_private,
            self.agent_id,
            self.challenge,
            self.token_hash,
        )

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete(signature=signature)

    def test_wrong_challenge(self):
        with self.assertRaises(RecoverableEnrollmentError):
            self.complete(challenge=generate_challenge())

    def test_invalid_hash(self):
        with self.assertRaises(RecoverableEnrollmentError):
            self.complete(credential_hash="invalid")

    def test_revoked_agent(self):
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete()

    def test_expired_challenge(self):
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

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete()

    def test_existing_credential(self):
        agent_registry.issue_agent_credential(self.agent_id)

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete()

    def test_recovery_window_expired(self):
        self.complete()

        with closing(sqlite3.connect(self.db_path)) as db:
            with db:
                db.execute(
                    """
                    UPDATE agent_enrollments
                    SET completed_at =
                        '2000-01-01T00:00:00+00:00'
                    WHERE agent_id = ?
                    """,
                    (self.agent_id,),
                )

        with self.assertRaises(RecoverableEnrollmentError):
            self.complete()

    def test_retry_does_not_replace_credential(self):
        self.complete()
        self.complete()

        self.assertTrue(
            agent_registry.authenticate_agent(
                self.agent_id, self.token
            )
        )
        self.assertEqual(self.credential_count(), 1)


if __name__ == "__main__":
    unittest.main()
