"""Regression tests for Git commit identity validation."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/release-metadata.py"

spec = importlib.util.spec_from_file_location(
    "versionary_release_git_identity", SOURCE
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class GitIdentityTests(unittest.TestCase):

    def test_sha1_commit(self):
        with patch.object(release, "git", side_effect=["", "a" * 40]):
            self.assertEqual(release.committed_identity(), "a" * 40)

    def test_sha256_commit(self):
        with patch.object(release, "git", side_effect=["", "b" * 64]):
            self.assertEqual(release.committed_identity(), "b" * 64)

    def test_reject_short_commit(self):
        with patch.object(release, "git", side_effect=["", "a" * 39]):
            with self.assertRaises(ValueError):
                release.committed_identity()

    def test_reject_nonhex_commit(self):
        with patch.object(release, "git", side_effect=["", "z" * 40]):
            with self.assertRaises(ValueError):
                release.committed_identity()

    def test_reject_dirty_tracked_source(self):
        with patch.object(release, "git", return_value=" M agent/__main__.py"):
            with self.assertRaises(ValueError):
                release.committed_identity()

    def test_real_repository_commit(self):
        commit = release.git("rev-parse", "--verify", "HEAD^{commit}")
        self.assertRegex(commit, r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


if __name__ == "__main__":
    unittest.main()
