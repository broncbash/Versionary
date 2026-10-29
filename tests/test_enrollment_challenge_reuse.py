"""Tests for safe challenge reuse and expiration."""

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


class TestChallengeReuse(unittest.TestCase):

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

        _, public_key = generate_keypair()
        self.agent_id = str(uuid4())

        register_with_key(
            self.agent_id,
            "challenge-test",
            "arch",
            public_key,
        )

        self.assertTrue(
            agent_registry.approve_agent(self.agent_id)
        )

    def test_active_challenge_reused(self):
        first = enrollment_store.create_challenge(
            self.agent_id
        )
        second = enrollment_store.create_challenge(
            self.agent_id
        )

        self.assertEqual(first, second)

    def test_expired_challenge_replaced(self):
        first = enrollment_store.create_challenge(
            self.agent_id
        )

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

        second = enrollment_store.create_challenge(
            self.agent_id
        )

        self.assertNotEqual(first, second)

    def test_completed_agent_gets_no_challenge(self):
        enrollment_store.create_challenge(
            self.agent_id
        )

        with closing(sqlite3.connect(self.db_path)) as db:
            with db:
                db.execute(
                    """
                    UPDATE agent_enrollments
                    SET completed_at =
                        '2026-01-01T00:00:00+00:00'
                    WHERE agent_id = ?
                    """,
                    (self.agent_id,),
                )

        self.assertIsNone(
            enrollment_store.create_challenge(
                self.agent_id
            )
        )

    def test_revoked_agent_gets_no_challenge(self):
        self.assertTrue(
            agent_registry.revoke_agent(self.agent_id)
        )

        self.assertIsNone(
            enrollment_store.create_challenge(
                self.agent_id
            )
        )


if __name__ == "__main__":
    unittest.main()
