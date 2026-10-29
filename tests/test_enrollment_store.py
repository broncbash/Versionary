"""Tests for enrollment persistence and key-binding safety."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import agent_registry
import enrollment_store
from enrollment_crypto import generate_keypair
from enrollment_v2 import register_with_key


class TestEnrollmentStore(unittest.TestCase):

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

        self.private_key, self.public_key = generate_keypair()
        self.agent_id = str(uuid4())

        register_with_key(
            self.agent_id,
            "test-node",
            "arch",
            self.public_key,
        )

    def test_key_bound_before_approval(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            row = db.execute(
                """
                SELECT e.public_key, a.status
                FROM agent_enrollments e
                JOIN agents a ON a.id = e.agent_id
                WHERE e.agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()

        self.assertEqual(row, (self.public_key, "pending"))

    def test_pending_agent_cannot_request_challenge(self):
        self.assertIsNone(
            enrollment_store.create_challenge(self.agent_id)
        )

    def test_approved_agent_can_request_challenge(self):
        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )
        self.assertIsNotNone(
            enrollment_store.create_challenge(self.agent_id)
        )

    def test_duplicate_registration_cannot_replace_key(self):
        _, other_key = generate_keypair()

        from enrollment_v2 import EnrollmentConflictError

        with self.assertRaises(EnrollmentConflictError):
            register_with_key(
                self.agent_id,
                "test-node",
                "arch",
                other_key,
            )

        with closing(sqlite3.connect(self.db_path)) as db:
            stored = db.execute(
                """
                SELECT public_key FROM agent_enrollments
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()[0]

        self.assertEqual(stored, self.public_key)

    def test_revoked_agent_cannot_request_challenge(self):
        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )
        self.assertIsNone(
            enrollment_store.create_challenge(self.agent_id)
        )


if __name__ == "__main__":
    unittest.main()
