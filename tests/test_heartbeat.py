import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import agent_registry as registry


class TestHeartbeat(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"

        self.path_patch = patch.object(
            registry, "DB_PATH", self.db_path
        )
        self.path_patch.start()

        registry.initialize_database()

        self.agent_id = registry.register_agent(
            "heartbeat-test", "arch"
        )
        registry.approve_agent(self.agent_id)

        self.token = registry.issue_agent_credential(
            self.agent_id
        )
        self.assertIsNotNone(self.token)

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def get_last_seen(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            row = db.execute(
                "SELECT last_seen FROM agents WHERE id = ?",
                (self.agent_id,),
            ).fetchone()
            return row[0]

    def test_valid_heartbeat(self):
        self.assertIsNone(self.get_last_seen())

        self.assertTrue(
            registry.record_agent_heartbeat(
                self.agent_id, self.token
            )
        )

        self.assertIsNotNone(self.get_last_seen())

    def test_invalid_token(self):
        self.assertFalse(
            registry.record_agent_heartbeat(
                self.agent_id, "wrong-token"
            )
        )

        self.assertIsNone(self.get_last_seen())

    def test_revoked_agent(self):
        registry.revoke_agent(self.agent_id)

        self.assertFalse(
            registry.record_agent_heartbeat(
                self.agent_id, self.token
            )
        )

        self.assertIsNone(self.get_last_seen())

    def test_revoked_credential(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute(
                """
                UPDATE agent_credentials
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE agent_id = ?
                """,
                (self.agent_id,),
            )

        self.assertFalse(
            registry.record_agent_heartbeat(
                self.agent_id, self.token
            )
        )

        self.assertIsNone(self.get_last_seen())

    def test_unknown_agent(self):
        self.assertFalse(
            registry.record_agent_heartbeat(
                "unknown-agent", self.token
            )
        )


if __name__ == "__main__":
    unittest.main()
