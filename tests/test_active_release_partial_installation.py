"""Partial-installation compatibility and safety tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "installer"

spec = importlib.util.spec_from_file_location(
    "versionary_partial_release_inspection",
    HERE / "active-release-inspection.py",
)

inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class PartialInstallationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name) / "root"
        self.root.mkdir(mode=0o700)

    def test_no_opt_directory(self):
        result = inspector.inspect(self.root)
        self.assertFalse(result["active_present"])

    def test_opt_without_application(self):
        (self.root / "opt").mkdir()
        result = inspector.inspect(self.root)
        self.assertFalse(result["active_present"])

    def test_application_without_releases(self):
        (self.root / "opt/versionary-agent").mkdir(parents=True)
        result = inspector.inspect(self.root)
        self.assertFalse(result["active_present"])

    def test_application_with_empty_releases(self):
        app = self.root / "opt/versionary-agent"
        (app / "releases").mkdir(parents=True)
        result = inspector.inspect(self.root)
        self.assertFalse(result["active_present"])

    def test_symlinked_opt_rejected(self):
        (self.root / "opt").symlink_to(self.root)
        with self.assertRaises(ValueError):
            inspector.inspect(self.root)

    def test_symlinked_application_rejected(self):
        (self.root / "opt").mkdir()
        (self.root / "opt/versionary-agent").symlink_to(self.root)
        with self.assertRaises(ValueError):
            inspector.inspect(self.root)

    def test_symlinked_releases_rejected_without_active_pointer(self):
        app = self.root / "opt/versionary-agent"
        app.mkdir(parents=True)
        (app / "releases").symlink_to(self.root)

        with self.assertRaises(ValueError):
            inspector.inspect(self.root)

    def test_regular_file_releases_rejected(self):
        app = self.root / "opt/versionary-agent"
        app.mkdir(parents=True)
        (app / "releases").write_text("unsafe")

        with self.assertRaises(ValueError):
            inspector.inspect(self.root)


if __name__ == "__main__":
    unittest.main()
