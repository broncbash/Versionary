"""Additional credential path security tests."""

import tempfile
import unittest
from pathlib import Path

from agent.credentials import (
    CredentialError,
    load_credential,
    save_credential,
)


class TestCredentialPathSecurity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_reject_symlinked_parent_on_save(self):
        alias = self.root / "alias"
        alias.symlink_to(self.private, target_is_directory=True)

        with self.assertRaises(CredentialError):
            save_credential("test-token", alias / "credential.json")

    def test_reject_symlinked_parent_on_load(self):
        real = self.private / "credential.json"
        save_credential("test-token", real)

        alias = self.root / "alias"
        alias.symlink_to(self.private, target_is_directory=True)

        with self.assertRaises(CredentialError):
            load_credential(alias / "credential.json")

    def test_reject_nested_symlink(self):
        nested = self.private / "nested"
        nested.mkdir(mode=0o700)

        alias = self.root / "alias"
        alias.symlink_to(self.private, target_is_directory=True)

        with self.assertRaises(CredentialError):
            save_credential(
                "test-token",
                alias / "nested" / "credential.json",
            )

    def test_normal_private_directory(self):
        path = self.private / "credential.json"

        save_credential("test-token", path)

        self.assertEqual(
            load_credential(path),
            "test-token",
        )


if __name__ == "__main__":
    unittest.main()
