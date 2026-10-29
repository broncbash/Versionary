"""Tests for persistent ARBY PATCH AGENT identity."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path

from agent.identity import (
    create_identity,
    get_or_create_identity,
    load_identity,
)


class TestAgentIdentity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "agent" / "identity.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_create_identity(self):
        identity = create_identity(
            "monitoring", "arch", self.path
        )

        uuid.UUID(identity["agent_id"])

        self.assertEqual(identity["hostname"], "monitoring")
        self.assertEqual(identity["platform"], "arch")
        self.assertEqual(
            self.path.stat().st_mode & 0o777,
            0o600,
        )

    def test_identity_persists(self):
        first = get_or_create_identity(
            "monitoring", "arch", self.path
        )

        second = get_or_create_identity(
            "monitoring", "arch", self.path
        )

        self.assertEqual(first, second)

    def test_no_overwrite(self):
        create_identity("monitoring", "arch", self.path)

        with self.assertRaises(FileExistsError):
            create_identity("other", "debian", self.path)

    def test_missing_identity(self):
        self.assertIsNone(load_identity(self.path))

    def test_corrupt_identity_rejected(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            '{"agent_id":"invalid","hostname":"x","platform":"arch"}'
        )

        with self.assertRaises(ValueError):
            load_identity(self.path)

    def test_identity_file_contents(self):
        created = create_identity(
            "monitoring", "arch", self.path
        )

        stored = json.loads(self.path.read_text())

        self.assertEqual(stored, created)


if __name__ == "__main__":
    unittest.main()
