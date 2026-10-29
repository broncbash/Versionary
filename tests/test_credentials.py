import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

import agent_registry as registry
from agent_auth import verify_agent_token


class TestCredentials(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"

        self.path_patch = patch.object(
            registry, "DB_PATH", self.db_path
        )
        self.path_patch.start()
        registry.initialize_database()

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def test_pending_agent_rejected(self):
        agent_id = registry.register_agent("test", "arch")
        self.assertIsNone(
            registry.issue_agent_credential(agent_id)
        )

    def test_approved_agent_receives_credential(self):
        agent_id = registry.register_agent("test", "arch")
        registry.approve_agent(agent_id)

        token = registry.issue_agent_credential(agent_id)

        self.assertIsNotNone(token)

        with closing(sqlite3.connect(self.db_path)) as db, db:
            stored_hash = db.execute(
                "SELECT token_hash FROM agent_credentials "
                "WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()[0]

        self.assertTrue(
            verify_agent_token(token, stored_hash)
        )
        self.assertNotEqual(token, stored_hash)

    def test_duplicate_issuance_rejected(self):
        agent_id = registry.register_agent("test", "arch")
        registry.approve_agent(agent_id)

        self.assertIsNotNone(
            registry.issue_agent_credential(agent_id)
        )
        self.assertIsNone(
            registry.issue_agent_credential(agent_id)
        )

    def test_revoked_agent_rejected(self):
        agent_id = registry.register_agent("test", "arch")
        registry.approve_agent(agent_id)
        registry.revoke_agent(agent_id)

        self.assertIsNone(
            registry.issue_agent_credential(agent_id)
        )

    def test_unknown_agent_rejected(self):
        self.assertIsNone(
            registry.issue_agent_credential("unknown")
        )


if __name__ == "__main__":
    unittest.main()
