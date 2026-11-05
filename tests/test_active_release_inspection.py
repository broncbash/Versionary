"""Security regression tests for isolated active release inspection."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "installer"
SPEC = importlib.util.spec_from_file_location(
    "active_release_inspection",
    HERE / "active-release-inspection.py",
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ActiveReleaseInspectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name) / "root"
        self.root.mkdir(mode=0o700)

        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.releases = self.app / "releases"
        self.releases.mkdir()

        self.identifier = "a" * 64
        self.release = self.releases / self.identifier / "agent"
        self.release.mkdir(parents=True)

    def test_valid_active_release(self):
        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )
        result = module.inspect(self.root)
        self.assertTrue(result["active_present"])
        self.assertEqual(result["active_release"], self.identifier)
        self.assertFalse(result["changes_made"])

    def test_missing_active_release(self):
        result = module.inspect(self.root)
        self.assertFalse(result["active_present"])
        self.assertIsNone(result["active_release"])

    def test_live_root_refused(self):
        with self.assertRaises(ValueError):
            module.inspect("/")

    def test_absolute_symlink_refused(self):
        (self.app / "agent").symlink_to("/etc")
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_traversal_refused(self):
        (self.app / "agent").symlink_to("../outside")
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_invalid_identifier_refused(self):
        (self.app / "agent").symlink_to("releases/bad/agent")
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_regular_file_pointer_refused(self):
        (self.app / "agent").write_text("not a symlink")
        with self.assertRaises(ValueError):
            module.inspect(self.root)

    def test_symlinked_releases_refused(self):
        self.releases.rmdir() if not any(self.releases.iterdir()) else None
        # Replace only the isolated test directory.
        for child in self.releases.iterdir():
            for nested in child.iterdir():
                nested.rmdir()
            child.rmdir()
        self.releases.rmdir()
        self.releases.symlink_to(self.root)

        with self.assertRaises(ValueError):
            module.inspect(self.root)


if __name__ == "__main__":
    unittest.main()
