"""Tests for manual, recoverable enrollment coordination."""

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from agent.credentials import load_credential
from agent.enrollment_client import (
    register_v2,
    complete_v2,
    EnrollmentClientError,
)
from agent.enrollment_journal import load_journal


class TestEnrollmentClient(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        root = Path(self.temp.name)
        self.key = root / "state" / "key.json"
        self.journal = root / "state" / "journal.json"
        self.credential = root / "state" / "credential.json"

        self.identity = {
            "agent_id": str(uuid4()),
            "hostname": "test-agent",
            "platform": "arch",
        }

    def kwargs(self):
        return {
            "key_path": self.key,
            "journal_path": self.journal,
            "credential_path": self.credential,
        }

    def test_registration(self):
        def fake_post(path, payload):
            self.assertEqual(path, "/api/v2/agents/register")
            self.assertIn("public_key", payload)
            return {
                "agent_id": self.identity["agent_id"],
                "status": "pending",
            }

        result = register_v2(
            self.identity,
            key_path=self.key,
            post=fake_post,
        )

        self.assertEqual(result["status"], "pending")

    def test_complete_enrollment(self):
        requests = []

        def fake_post(path, payload):
            requests.append((path, payload))

            if path.endswith("/challenge"):
                return {
                    "agent_id": self.identity["agent_id"],
                    "challenge": "A" * 43,
                }

            return {
                "agent_id": self.identity["agent_id"],
                "status": "enrolled",
                "recovered": False,
            }

        result = complete_v2(
            self.identity,
            post=fake_post,
            **self.kwargs(),
        )

        self.assertEqual(result["status"], "enrolled")
        self.assertTrue(load_credential(self.credential))
        self.assertIsNone(load_journal(self.journal))
        self.assertEqual(len(requests), 2)

    def test_lost_response_recovery(self):
        requests = []

        def failing_post(path, payload):
            requests.append((path, payload))

            if path.endswith("/challenge"):
                return {
                    "agent_id": self.identity["agent_id"],
                    "challenge": "A" * 43,
                }

            raise ConnectionError("Simulated lost response")

        with self.assertRaises(ConnectionError):
            complete_v2(
                self.identity,
                post=failing_post,
                **self.kwargs(),
            )

        journal = load_journal(self.journal)
        self.assertIsNotNone(journal)

        def recovery_post(path, payload):
            self.assertTrue(path.endswith("/complete"))
            self.assertEqual(
                payload["credential_hash"],
                journal["credential_hash"],
            )
            self.assertEqual(
                payload["signature"],
                journal["signature"],
            )
            return {
                "agent_id": self.identity["agent_id"],
                "status": "enrolled",
                "recovered": True,
            }

        result = complete_v2(
            self.identity,
            post=recovery_post,
            **self.kwargs(),
        )

        self.assertTrue(result["recovered"])
        self.assertIsNone(load_journal(self.journal))
        self.assertTrue(load_credential(self.credential))

    def test_already_provisioned(self):
        def fake_post(path, payload):
            if path.endswith("/challenge"):
                return {
                    "agent_id": self.identity["agent_id"],
                    "challenge": "A" * 43,
                }
            return {
                "agent_id": self.identity["agent_id"],
                "status": "enrolled",
                "recovered": False,
            }

        complete_v2(
            self.identity,
            post=fake_post,
            **self.kwargs(),
        )

        def no_network(path, payload):
            self.fail("Already provisioned agent contacted server")

        result = complete_v2(
            self.identity,
            post=no_network,
            **self.kwargs(),
        )

        self.assertEqual(result["status"], "already-provisioned")

    def test_wrong_journal_identity(self):
        def failing_post(path, payload):
            if path.endswith("/challenge"):
                return {
                    "agent_id": self.identity["agent_id"],
                    "challenge": "A" * 43,
                }
            raise ConnectionError("Simulated interruption")

        with self.assertRaises(ConnectionError):
            complete_v2(
                self.identity,
                post=failing_post,
                **self.kwargs(),
            )

        other_identity = dict(self.identity)
        other_identity["agent_id"] = str(uuid4())

        with self.assertRaises(EnrollmentClientError):
            complete_v2(
                other_identity,
                post=lambda *_: self.fail("Unexpected network"),
                **self.kwargs(),
            )


if __name__ == "__main__":
    unittest.main()
