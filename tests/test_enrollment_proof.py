"""Isolated tests for enrollment proof verification."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import agent_registry
import enrollment_store
from enrollment_crypto import (
    generate_keypair,
    generate_challenge,
    sign_challenge,
)
from enrollment_proof import verify_enrollment_proof
from enrollment_v2 import register_with_key


class TestEnrollmentProof(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        db_path = Path(self.temp.name) / "agents.db"
        patcher = patch.object(
            agent_registry, "DB_PATH", db_path
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        agent_registry.initialize_database()

        self.private_key, public_key = generate_keypair()
        self.agent_id = str(uuid4())

        register_with_key(
            self.agent_id,
            "test-agent",
            "arch",
            public_key,
        )

        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )

        self.challenge = enrollment_store.create_challenge(
            self.agent_id
        )
        self.assertIsNotNone(self.challenge)

    def sign(self, challenge=None):
        return sign_challenge(
            self.private_key,
            challenge or self.challenge,
        )

    def test_valid_proof(self):
        self.assertTrue(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                self.sign(),
            )
        )

    def test_wrong_private_key(self):
        other_private, _ = generate_keypair()

        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                sign_challenge(other_private, self.challenge),
            )
        )

    def test_wrong_challenge(self):
        wrong = generate_challenge()

        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                wrong,
                self.sign(wrong),
            )
        )

    def test_invalid_signature(self):
        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                "invalid",
            )
        )

    def test_unknown_agent(self):
        self.assertFalse(
            verify_enrollment_proof(
                str(uuid4()),
                self.challenge,
                self.sign(),
            )
        )

    def test_consumed_challenge(self):
        self.assertTrue(
            enrollment_store.consume_challenge(
                self.agent_id,
                self.challenge,
            )
        )

        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                self.sign(),
            )
        )

    def test_revoked_agent(self):
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )

        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                self.sign(),
            )
        )

    def test_existing_credential(self):
        agent_registry.issue_agent_credential(
            self.agent_id
        )

        self.assertFalse(
            verify_enrollment_proof(
                self.agent_id,
                self.challenge,
                self.sign(),
            )
        )


if __name__ == "__main__":
    unittest.main()
