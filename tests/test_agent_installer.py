"""Regression tests for ARBY PATCH AGENT installation."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_install_files",
    ROOT / "installer/install-files.py",
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

ARCHIVE = ROOT / "installer/dist/arby-patch-agent.tar.gz"


class TestAgentInstaller(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_fresh_installation(self):
        installer.install(ARCHIVE, self.root)

        agent = self.root / "opt/arby-patch-agent/agent"
        self.assertEqual(
            {p.name for p in agent.glob("*.py")},
            installer.MODULES,
        )

        state = self.root / "var/lib/arby-patch-agent"
        self.assertEqual(
            state.stat().st_mode & 0o777,
            0o700,
        )

    def test_reinstallation_preserves_identity(self):
        installer.install(ARCHIVE, self.root)

        state = self.root / "var/lib/arby-patch-agent"
        identity = state / "identity.json"
        credential = state / "credential.json"

        identity.write_text("persistent-identity")
        credential.write_text("persistent-credential")

        os.chmod(identity, 0o600)
        os.chmod(credential, 0o600)

        installer.install(ARCHIVE, self.root)

        self.assertEqual(
            identity.read_text(),
            "persistent-identity",
        )
        self.assertEqual(
            credential.read_text(),
            "persistent-credential",
        )

        self.assertEqual(
            identity.stat().st_mode & 0o777,
            0o600,
        )
        self.assertEqual(
            credential.stat().st_mode & 0o777,
            0o600,
        )

    def test_reject_symlinked_application_directory(self):
        outside = self.root / "outside"
        outside.mkdir()

        opt = self.root / "opt"
        opt.mkdir()
        (opt / "arby-patch-agent").symlink_to(
            outside, target_is_directory=True
        )

        with self.assertRaises(RuntimeError):
            installer.install(ARCHIVE, self.root)

    def test_reject_symlinked_module(self):
        agent = self.root / "opt/arby-patch-agent/agent"
        agent.mkdir(parents=True)

        target = self.root / "outside.py"
        target.write_text("do not modify")

        (agent / "identity.py").symlink_to(target)

        with self.assertRaises(RuntimeError):
            installer.install(ARCHIVE, self.root)

        self.assertEqual(
            target.read_text(),
            "do not modify",
        )

    def test_reject_file_in_directory_path(self):
        opt = self.root / "opt"
        opt.write_text("not a directory")

        with self.assertRaises(RuntimeError):
            installer.install(ARCHIVE, self.root)

    def test_reject_symlinked_installation_root(self):
        link = self.root.parent / (
            self.root.name + "-symlink"
        )
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)

        with self.assertRaises(RuntimeError):
            installer.install(ARCHIVE, link)


if __name__ == "__main__":
    unittest.main()
