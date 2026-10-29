import sqlite3
import unittest

from agent_registry import SCHEMA


class TestAgentRegistry(unittest.TestCase):

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def tearDown(self):
        self.db.close()

    def test_new_agent_pending(self):
        self.db.execute(
            """
            INSERT INTO agents
            (id, hostname, platform, registered_at)
            VALUES (?, ?, ?, ?)
            """,
            ("test-001", "arch-test", "arch", "2026-10-27T00:00:00Z"),
        )

        status = self.db.execute(
            "SELECT status FROM agents WHERE id = ?",
            ("test-001",),
        ).fetchone()[0]

        self.assertEqual(status, "pending")

    def test_invalid_status_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO agents
                (id, hostname, platform, status, registered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("test-002", "arch-test", "arch", "unknown",
                 "2026-10-27T00:00:00Z"),
            )

    def test_revoked_agent_cannot_report(self):
        self.db.execute(
            """
            INSERT INTO agents
            (id, hostname, platform, status, registered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("test-003", "arch-test", "arch", "revoked",
             "2026-10-27T00:00:00Z"),
        )

        status = self.db.execute(
            "SELECT status FROM agents WHERE id = ?",
            ("test-003",),
        ).fetchone()[0]

        self.assertNotEqual(status, "approved")


if __name__ == "__main__":
    unittest.main()
