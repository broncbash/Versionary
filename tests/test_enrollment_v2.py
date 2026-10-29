"""Tests for atomic, key-bound v2 registration."""

import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import agent_registry
from enrollment_crypto import generate_keypair
from enrollment_v2 import (
    register_with_key,
    EnrollmentConflictError,
    EnrollmentRegistrationError,
)


class TestEnrollmentV2(unittest.TestCase):

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

        self.agent_id = str(uuid4())
        _, self.public_key = generate_keypair()

    def register(self, **overrides):
        data = {
            "agent_id": self.agent_id,
            "hostname": "monitor-test",
            "platform": "arch",
            "public_key": self.public_key,
        }
        data.update(overrides)
        return register_with_key(**data)

    def test_registration_creates_pending_agent(self):
        result = self.register()
        self.assertEqual(result["status"], "pending")

        with closing(sqlite3.connect(self.db_path)) as db:
            row = db.execute(
                "SELECT status FROM agents WHERE id = ?",
                (self.agent_id,),
            ).fetchone()

        self.assertEqual(row[0], "pending")

    def test_public_key_bound_at_registration(self):
        self.register()

        with closing(sqlite3.connect(self.db_path)) as db:
            row = db.execute(
                """
                SELECT public_key
                FROM agent_enrollments
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()

        self.assertEqual(row[0], self.public_key)

    def test_duplicate_registration_rejected(self):
        self.register()

        with self.assertRaises(EnrollmentConflictError):
            self.register()

    def test_key_substitution_rejected(self):
        self.register()
        _, other_key = generate_keypair()

        with self.assertRaises(EnrollmentConflictError):
            self.register(public_key=other_key)

        with closing(sqlite3.connect(self.db_path)) as db:
            stored = db.execute(
                """
                SELECT public_key FROM agent_enrollments
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            ).fetchone()[0]

        self.assertEqual(stored, self.public_key)

    def test_invalid_public_key_rejected(self):
        with self.assertRaises(EnrollmentRegistrationError):
            self.register(public_key="invalid")

    def test_invalid_hostname_rejected(self):
        with self.assertRaises(EnrollmentRegistrationError):
            self.register(hostname=" ")

    def test_invalid_uuid_rejected(self):
        with self.assertRaises(EnrollmentRegistrationError):
            self.register(agent_id="not-a-uuid")

    def test_failed_registration_creates_no_agent(self):
        with self.assertRaises(EnrollmentRegistrationError):
            self.register(public_key="invalid")

        with closing(sqlite3.connect(self.db_path)) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM agents"
            ).fetchone()[0]

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
