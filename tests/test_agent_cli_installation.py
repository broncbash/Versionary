"""Offline regression tests for verified CLI distribution installation."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/install-agent-cli.py"
BUNDLE = (
    ROOT / "installer/dist/"
    "versionary-agent-distribution-26l.tar.gz"
)

spec = importlib.util.spec_from_file_location(
    "versionary_cli_installer", SOURCE
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AgentCLIInstallationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

    def test_verified_install(self):
        result = module.install(self.root, BUNDLE)
        self.assertEqual(
            result.read_bytes(),
            (ROOT / "versionary_agent_cli.py").read_bytes(),
        )
        self.assertEqual(result.stat().st_mode & 0o777, 0o644)

    def test_installed_cli_supports_system_mode(self):
        target = module.install(self.root, BUNDLE)
        source = target.read_text(encoding="utf-8")

        self.assertIn('"--system"', source)
        self.assertIn("read_system_config", source)
        self.assertIn("SYSTEM_STATE", source)

    def test_identical_reinstall_preserves_inode(self):
        first = module.install(self.root, BUNDLE)
        before = first.stat().st_ino
        second = module.install(self.root, BUNDLE)
        self.assertEqual(before, second.stat().st_ino)

    def test_modified_existing_cli_is_preserved(self):
        target = self.app / "versionary_agent_cli.py"
        target.write_text("existing local data")

        with self.assertRaises(ValueError):
            module.install(self.root, BUNDLE)

        self.assertEqual(target.read_text(), "existing local data")

    def test_symlinked_cli_is_rejected(self):
        target = self.app / "versionary_agent_cli.py"
        target.symlink_to(self.root / "outside")

        with self.assertRaises(ValueError):
            module.install(self.root, BUNDLE)

    def test_symlinked_application_directory_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.app.rmdir()
        self.app.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(ValueError):
            module.install(self.root, BUNDLE)

    def test_production_root_is_rejected(self):
        with self.assertRaises(ValueError):
            module.install("/", BUNDLE)

    def test_invalid_bundle_does_not_create_cli(self):
        with tempfile.TemporaryDirectory() as temporary:
            bad = Path(temporary) / "invalid.tar.gz"
            bad.write_bytes(b"invalid distribution")

            with self.assertRaises(Exception):
                module.install(self.root, bad)

            self.assertFalse(
                (self.app / "versionary_agent_cli.py").exists()
            )

    def test_bundle_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / "bundle.tar.gz"
            link.symlink_to(BUNDLE)

            with self.assertRaises(ValueError):
                module.install(self.root, link)

    def test_credentials_and_identity_untouched(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True, mode=0o700)

        credential = state / "credential.json"
        identity = state / "identity.json"

        credential.write_bytes(b"TEST-CREDENTIAL")
        identity.write_bytes(b"TEST-IDENTITY")

        os.chmod(credential, 0o600)
        os.chmod(identity, 0o600)

        module.install(self.root, BUNDLE)

        self.assertEqual(credential.read_bytes(), b"TEST-CREDENTIAL")
        self.assertEqual(identity.read_bytes(), b"TEST-IDENTITY")

    def test_verification_failure_precedes_installation(self):
        with patch.object(
            module,
            "verified_cli",
            side_effect=ValueError("Rejected distribution"),
        ):
            with self.assertRaisesRegex(
                ValueError, "Rejected distribution"
            ):
                module.install(self.root, BUNDLE)

        self.assertFalse(
            (self.app / "versionary_agent_cli.py").exists()
        )


if __name__ == "__main__":
    unittest.main()
