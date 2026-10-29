import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_registry as registry


class TestAgentLifecycle(unittest.TestCase):

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

    def test_registration_and_approval(self):
        agent_id = registry.register_agent(
            "arch-test", "arch"
        )

        self.assertFalse(
            registry.is_agent_approved(agent_id)
        )

        self.assertTrue(
            registry.approve_agent(agent_id)
        )

        self.assertTrue(
            registry.is_agent_approved(agent_id)
        )

    def test_revocation_is_permanent(self):
        agent_id = registry.register_agent(
            "debian-test", "debian"
        )

        registry.approve_agent(agent_id)

        self.assertTrue(
            registry.revoke_agent(agent_id)
        )

        self.assertFalse(
            registry.is_agent_approved(agent_id)
        )

        self.assertFalse(
            registry.approve_agent(agent_id)
        )

    def test_unknown_agent_rejected(self):
        self.assertFalse(
            registry.is_agent_approved("unknown-agent")
        )

        self.assertFalse(
            registry.approve_agent("unknown-agent")
        )

    def test_invalid_registration(self):
        with self.assertRaises(ValueError):
            registry.register_agent("", "arch")

    def test_duplicate_registration_creates_distinct_identities(self):
        first_id = registry.register_agent("arch-test", "arch")
        second_id = registry.register_agent("arch-test", "arch")

        self.assertNotEqual(first_id, second_id)

    def test_registration_preserves_agent_id(self):
        from uuid import uuid4

        expected_id = str(uuid4())

        actual_id = registry.register_agent(
            "arch-test",
            "arch",
            agent_id=expected_id,
        )

        self.assertEqual(actual_id, expected_id)

    def test_registration_rejects_invalid_agent_id(self):
        with self.assertRaises(ValueError):
            registry.register_agent(
                "arch-test",
                "arch",
                agent_id="not-a-valid-uuid",
            )

    def test_duplicate_agent_id_rejected(self):
        from uuid import uuid4
        import sqlite3

        agent_id = str(uuid4())

        registry.register_agent(
            "arch-test",
            "arch",
            agent_id=agent_id,
        )

        with self.assertRaises(sqlite3.IntegrityError):
            registry.register_agent(
                "arch-test",
                "arch",
                agent_id=agent_id,
            )


if __name__ == "__main__":
    unittest.main()
