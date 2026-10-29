"""Read-only installation inventory security tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

file = Path(__file__).resolve().parents[1] / "installer/installation-inventory.py"
spec = importlib.util.spec_from_file_location("installation_inventory", file)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InstallationInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_empty_root_reports_absence(self):
        result = inventory.inspect(self.root)
        self.assertEqual(result["status"], "inspected")
        self.assertFalse(result["backup_created"])
        self.assertTrue(all(not item["present"] for item in result["assets"].values()))

    def test_hashes_existing_configuration_without_mutation(self):
        config = self.root / "etc/arby-patch-agent/config.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"server":"https://example.test"}')
        before = config.read_bytes()
        result = inventory.inspect(self.root)
        self.assertTrue(result["assets"]["etc/arby-patch-agent/config.json"]["present"])
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse(result["changes_made"])

    def test_symlink_asset_rejected(self):
        config = self.root / "etc/arby-patch-agent/config.json"
        config.parent.mkdir(parents=True)
        config.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):
            inventory.inspect(self.root)

    def test_symlink_ancestor_rejected(self):
        (self.root / "etc").symlink_to("/etc")
        with self.assertRaises(ValueError):
            inventory.inspect(self.root)

    def test_private_state_contents_not_read(self):
        state = self.root / "var/lib/arby-patch-agent"
        state.mkdir(parents=True, mode=0o700)
        (state / "secret").write_text("private")
        result = inventory.inspect(self.root)
        self.assertEqual(result["private_state"], "present-not-inspected")
        self.assertFalse(result["credential_contents_read"])

    def test_production_root_rejected(self):
        with self.assertRaises(ValueError):
            inventory.inspect("/")
