import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import agent_registry as registry


class TestScanReporting(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "agents.db"

        self.path_patch = patch.object(
            registry, "DB_PATH", self.db_path
        )
        self.path_patch.start()

        registry.initialize_database()

        self.agent_id = registry.register_agent(
            "scan-test", "arch"
        )
        registry.approve_agent(self.agent_id)

        self.token = registry.issue_agent_credential(
            self.agent_id
        )
        self.assertIsNotNone(self.token)

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def get_reports(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return db.execute(
                """
                SELECT status, count, packages_json, error
                FROM scan_reports
                """
            ).fetchall()

    def test_valid_scan(self):
        packages = [
            {
                "name": "linux",
                "installed": "6.11",
                "available": "6.12",
            },
            {
                "name": "neovim",
                "installed": "0.10",
                "available": "0.11",
            },
    ]

        self.assertTrue(
            registry.record_agent_scan(
                self.agent_id,
                self.token,
                "success",
                packages,
            )
        )

        reports = self.get_reports()

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][0], "success")
        self.assertEqual(reports[0][1], 2)
        self.assertEqual(
            json.loads(reports[0][2]),
            [
                {**package, "repository": None}
                for package in packages
            ],
        )

    def test_invalid_token(self):
        self.assertFalse(
            registry.record_agent_scan(
                self.agent_id, "wrong", "success", []
            )
        )
        self.assertEqual(len(self.get_reports()), 0)

    def test_revoked_agent(self):
        registry.revoke_agent(self.agent_id)

        self.assertFalse(
            registry.record_agent_scan(
                self.agent_id, self.token, "success", []
            )
        )
        self.assertEqual(len(self.get_reports()), 0)

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
            registry.record_agent_scan(
                self.agent_id, self.token, "success", []
            )
        )
        self.assertEqual(len(self.get_reports()), 0)

    def test_invalid_status(self):
        self.assertFalse(
            registry.record_agent_scan(
                self.agent_id, self.token, "unknown", []
            )
        )
        self.assertEqual(len(self.get_reports()), 0)

    def test_error_report(self):
        self.assertTrue(
            registry.record_agent_scan(
                self.agent_id,
                self.token,
                "error",
                [],
                "Package manager unavailable",
            )
        )

        reports = self.get_reports()

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0][0], "error")
        self.assertIsNone(reports[0][1])
        self.assertEqual(
            reports[0][3], "Package manager unavailable"
        )


if __name__ == "__main__":
    unittest.main()
