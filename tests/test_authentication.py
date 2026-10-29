import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

import agent_registry as registry


class TestAuthentication(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"

        self.path_patch = patch.object(
            registry, "DB_PATH", self.db_path
        )
        self.path_patch.start()
        registry.initialize_database()

        self.agent_id = registry.register_agent(
            "arch-test", "arch"
        )
        registry.approve_agent(self.agent_id)
        self.token = registry.issue_agent_credential(
            self.agent_id
        )
        self.assertIsNotNone(self.token)

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def test_valid_credential(self):
        self.assertTrue(
            registry.authenticate_agent(
                self.agent_id, self.token
            )
        )

    def test_invalid_credential(self):
        self.assertFalse(
            registry.authenticate_agent(
                self.agent_id, "incorrect-token"
            )
        )

    def test_unknown_agent(self):
        self.assertFalse(
            registry.authenticate_agent(
                "unknown-agent", self.token
            )
        )

    def test_revoked_agent(self):
        registry.revoke_agent(self.agent_id)

        self.assertFalse(
            registry.authenticate_agent(
                self.agent_id, self.token
            )
        )

    def test_revoked_credential(self):
        import sqlite3
        from datetime import datetime, timezone

        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute(
                """
                UPDATE agent_credentials
                SET revoked_at = ?
                WHERE agent_id = ?
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    self.agent_id,
                ),
            )

        self.assertFalse(
            registry.authenticate_agent(
                self.agent_id, self.token
            )
        )


if __name__ == "__main__":
    unittest.main()
