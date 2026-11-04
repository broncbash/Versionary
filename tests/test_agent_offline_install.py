"""Offline tests for the consolidated installer coordinator."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/install-agent-offline.py"

spec = importlib.util.spec_from_file_location(
    "versionary_offline_install", SCRIPT
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OfflineInstallerTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_rejects_production_root(self):
        with self.assertRaises(ValueError):
            module.check_root("/")

    def test_accepts_private_isolated_root(self):
        self.assertEqual(
            module.check_root(self.root),
            self.root,
        )

    def test_rejects_symlink_root(self):
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)

        with self.assertRaises(ValueError):
            module.check_root(link)

    def test_invalid_bundle_never_invokes_installer(self):
        ca = self.root / "ca.crt"
        ca.write_text("test")

        with patch.object(
            module,
            "run_helper",
        ) as installer:
            with self.assertRaises(Exception):
                module.install(
                    self.root,
                    self.root / "missing.tar.gz",
                    "https://example.test",
                    ca,
                )

        installer.assert_not_called()

    def test_invalid_server_never_invokes_installer(self):
        ConfigurationError = module.CONFIG.ConfigurationError
        ca = self.root / "ca.crt"
        ca.write_text("test")

        bundle = (
            ROOT / "installer/dist/"
            "versionary-agent-distribution-26l.tar.gz"
        )

        with patch.object(
            module,
            "run_helper",
        ) as installer:
            with self.assertRaises(ConfigurationError):
                module.install(
                    self.root,
                    bundle,
                    "http://insecure.example.test",
                    ca,
                )

        installer.assert_not_called()

    def test_missing_ca_never_invokes_installer(self):
        bundle = (
            ROOT / "installer/dist/"
            "versionary-agent-distribution-26l.tar.gz"
        )

        with patch.object(
            module,
            "run_helper",
        ) as installer:
            with self.assertRaises(ValueError):
                module.install(
                    self.root,
                    bundle,
                    "https://example.test",
                    self.root / "missing.crt",
                )

        installer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
