"""Tests for secure, persistent agent enrollment keys."""

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from agent.enrollment_keys import (
    create_keypair,
    load_keypair,
    get_or_create_keypair,
    EnrollmentKeyError,
)


class TestEnrollmentKeys(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.state = Path(self.temp.name) / "state"
        self.path = self.state / "enrollment-key.json"

    def test_create_and_load(self):
        created = create_keypair(self.path)
        loaded = load_keypair(self.path)

        self.assertEqual(created, loaded)

    def test_private_permissions(self):
        create_keypair(self.path)

        self.assertEqual(
            stat.S_IMODE(self.state.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(self.path.stat().st_mode),
            0o600,
        )

    def test_reinstall_preserves_keypair(self):
        first = get_or_create_keypair(self.path)
        second = get_or_create_keypair(self.path)

        self.assertEqual(first, second)

    def test_exclusive_creation(self):
        first = create_keypair(self.path)

        with self.assertRaises(FileExistsError):
            create_keypair(self.path)

        self.assertEqual(load_keypair(self.path), first)

    def test_missing_key_returns_none(self):
        self.state.mkdir(mode=0o700)

        self.assertIsNone(load_keypair(self.path))

    def test_reject_file_symlink(self):
        self.state.mkdir(mode=0o700)

        target = self.state / "target.json"
        target.write_text("{}")
        os.chmod(target, 0o600)

        self.path.symlink_to(target)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)

    def test_reject_directory_symlink(self):
        real_state = Path(self.temp.name) / "real"
        real_state.mkdir(mode=0o700)
        self.state.symlink_to(real_state, target_is_directory=True)

        with self.assertRaises(EnrollmentKeyError):
            get_or_create_keypair(self.path)

    def test_reject_weak_file_permissions(self):
        create_keypair(self.path)
        os.chmod(self.path, 0o644)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)

    def test_reject_weak_directory_permissions(self):
        create_keypair(self.path)
        os.chmod(self.state, 0o755)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)

    def test_reject_mismatched_public_key(self):
        create_keypair(self.path)

        data = json.loads(self.path.read_text())
        data["public_key"] = "incorrect"
        self.path.write_text(json.dumps(data))
        os.chmod(self.path, 0o600)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)

    def test_reject_corrupted_private_key(self):
        create_keypair(self.path)

        data = json.loads(self.path.read_text())
        data["private_key"] = "invalid"
        self.path.write_text(json.dumps(data))
        os.chmod(self.path, 0o600)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)

    def test_reject_extra_fields(self):
        create_keypair(self.path)

        data = json.loads(self.path.read_text())
        data["unexpected"] = "value"
        self.path.write_text(json.dumps(data))
        os.chmod(self.path, 0o600)

        with self.assertRaises(EnrollmentKeyError):
            load_keypair(self.path)


if __name__ == "__main__":
    unittest.main()
