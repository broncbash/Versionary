"""Tests for crash-safe enrollment journal storage."""

import hashlib
import os
import secrets
import stat
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from agent.enrollment_crypto import (
    generate_keypair,
    sign_enrollment,
)
from agent.enrollment_journal import (
    save_journal,
    load_journal,
    delete_journal,
    EnrollmentJournalError,
)
from enrollment_crypto import generate_challenge


class TestEnrollmentJournal(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.state = Path(self.temp.name) / "state"
        self.path = self.state / "pending.json"

        private, public = generate_keypair()
        agent_id = str(uuid4())
        challenge = generate_challenge()
        token = secrets.token_urlsafe(48)
        credential_hash = hashlib.sha256(
            token.encode()
        ).hexdigest()

        self.entry = {
            "agent_id": agent_id,
            "challenge": challenge,
            "signature": sign_enrollment(
                private,
                agent_id,
                challenge,
                credential_hash,
            ),
            "credential_hash": credential_hash,
            "token": token,
        }

    def test_save_and_load(self):
        save_journal(self.entry, self.path)
        self.assertEqual(load_journal(self.path), self.entry)

    def test_private_permissions(self):
        save_journal(self.entry, self.path)

        self.assertEqual(
            stat.S_IMODE(self.state.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(self.path.stat().st_mode),
            0o600,
        )

    def test_refuse_overwrite(self):
        save_journal(self.entry, self.path)

        with self.assertRaises(FileExistsError):
            save_journal(self.entry, self.path)

        self.assertEqual(load_journal(self.path), self.entry)

    def test_missing_journal(self):
        self.state.mkdir(mode=0o700)
        self.assertIsNone(load_journal(self.path))

    def test_delete_verified_journal(self):
        save_journal(self.entry, self.path)

        self.assertTrue(delete_journal(self.path))
        self.assertFalse(self.path.exists())

    def test_reject_symlink(self):
        self.state.mkdir(mode=0o700)

        target = self.state / "target"
        target.write_text("{}")
        os.chmod(target, 0o600)

        self.path.symlink_to(target)

        with self.assertRaises(EnrollmentJournalError):
            load_journal(self.path)

    def test_reject_weak_permissions(self):
        save_journal(self.entry, self.path)
        os.chmod(self.path, 0o644)

        with self.assertRaises(EnrollmentJournalError):
            load_journal(self.path)

    def test_reject_hash_mismatch(self):
        entry = dict(self.entry)
        entry["credential_hash"] = "0" * 64

        with self.assertRaises(EnrollmentJournalError):
            save_journal(entry, self.path)

    def test_reject_extra_fields(self):
        entry = dict(self.entry)
        entry["unexpected"] = True

        with self.assertRaises(EnrollmentJournalError):
            save_journal(entry, self.path)


if __name__ == "__main__":
    unittest.main()
