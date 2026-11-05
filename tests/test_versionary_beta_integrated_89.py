"""Integrated full-install beta acceptance tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SOURCE = (
    BASE / "installer/versionary-agent-beta-integrated-install.py"
)

spec = importlib.util.spec_from_file_location(
    "versionary_integrated89", SOURCE
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(
            prefix="versionary-integrated89-"
        )
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_real_root_forbidden(self):
        with self.assertRaises(ValueError):
            module.validate_root("/")

    def test_relative_root_forbidden(self):
        with self.assertRaises(ValueError):
            module.validate_root("relative")

    def test_symlink_root_forbidden(self):
        link = self.root.parent / (
            self.root.name + "-link"
        )
        link.symlink_to(
            self.root, target_is_directory=True
        )
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            module.validate_root(link)

    def test_clear_inspection(self):
        self.assertEqual(
            module.inspect(self.root)["status"], "clear"
        )

    def test_marker_survives_inspection(self):
        module.create_marker(self.root)
        self.assertEqual(
            module.inspect(self.root)["status"],
            "recovery_required",
        )
        self.assertTrue(
            module.marker_path(self.root).exists()
        )

    def test_duplicate_marker_refused(self):
        module.create_marker(self.root)
        with self.assertRaises(FileExistsError):
            module.create_marker(self.root)

    def test_corrupt_marker_refused(self):
        module.marker_path(self.root).write_text("invalid")
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_symlink_marker_refused(self):
        target = self.root / "target"
        target.write_text("keep")
        module.marker_path(self.root).symlink_to(target)
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)
        self.assertEqual(target.read_text(), "keep")

    def test_missing_authorization(self):
        with self.assertRaises(PermissionError):
            module.run(
                self.root, "missing", "https://example.test",
                "missing", execute=True
            )

    def test_no_authorization_for_preview(self):
        with self.assertRaises(ValueError):
            module.run(
                self.root, "missing", "https://example.test",
                "missing", authorization=module.AUTHORIZATION
            )

    def test_pending_marker_blocks_prepare(self):
        module.create_marker(self.root)
        with self.assertRaises(RuntimeError):
            module.prepare(
                self.root, "missing",
                "https://example.test", "missing"
            )

    def test_no_real_system_install_path(self):
        source = SOURCE.read_text()
        self.assertIn(
            "Real-system installation disabled", source
        )
        self.assertNotIn("systemctl", source)


if __name__ == "__main__":
    unittest.main()
