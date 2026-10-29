"""Regression tests for atomic ARBY PATCH AGENT releases."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "installer/dist/arby-patch-agent.tar.gz"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_installer",
    ROOT / "installer/install-files.py",
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TestAtomicReleases(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def app(self):
        return self.root / "opt/arby-patch-agent"

    def test_fresh_install_uses_release_symlink(self):
        installer.install(ARCHIVE, self.root)

        active = self.app() / "agent"
        releases = self.app() / "releases"

        self.assertTrue(active.is_symlink())
        self.assertTrue(releases.is_dir())
        self.assertEqual(
            {p.name for p in active.glob("*.py")},
            installer.MODULES,
        )

        resolved = active.resolve()
        self.assertTrue(resolved.is_relative_to(releases.resolve()))

    def test_reinstall_preserves_active_release(self):
        installer.install(ARCHIVE, self.root)

        active = self.app() / "agent"
        original = os.readlink(active)

        installer.install(ARCHIVE, self.root)

        self.assertEqual(os.readlink(active), original)

    def test_failed_release_does_not_change_active(self):
        installer.install(ARCHIVE, self.root)

        active = self.app() / "agent"
        original = os.readlink(active)

        with patch.object(
            installer.validator,
            "load_modules",
            side_effect=ValueError("Simulated invalid archive"),
        ):
            with self.assertRaises(ValueError):
                installer.install(ARCHIVE, self.root)

        self.assertEqual(os.readlink(active), original)

    def test_state_survives_reinstallation(self):
        installer.install(ARCHIVE, self.root)

        state = self.root / "var/lib/arby-patch-agent"
        identity = state / "identity.json"
        credential = state / "credential.json"

        identity.write_text("persistent-identity")
        credential.write_text("persistent-credential")
        identity.chmod(0o600)
        credential.chmod(0o600)

        installer.install(ARCHIVE, self.root)

        self.assertEqual(identity.read_text(), "persistent-identity")
        self.assertEqual(credential.read_text(), "persistent-credential")
        self.assertEqual(identity.stat().st_mode & 0o777, 0o600)
        self.assertEqual(credential.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
