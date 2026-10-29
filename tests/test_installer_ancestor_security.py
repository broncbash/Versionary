"""Ancestor-directory security regression tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_ancestor_security_installer",
    ROOT / "installer/install-files.py",
)

installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TestAncestorSecurity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_safe_parent_accepted(self):
        parent = self.root / "opt"
        parent.mkdir(mode=0o755)

        installer.require_secure_ancestors(
            self.root / "opt/arby-patch-agent",
            self.root,
        )

    def test_group_writable_parent_rejected(self):
        parent = self.root / "opt"
        parent.mkdir()
        parent.chmod(0o775)

        with self.assertRaises(RuntimeError):
            installer.require_secure_ancestors(
                self.root / "opt/arby-patch-agent",
                self.root,
            )

    def test_world_writable_parent_rejected(self):
        parent = self.root / "opt"
        parent.mkdir()
        parent.chmod(0o777)

        with self.assertRaises(RuntimeError):
            installer.require_secure_ancestors(
                self.root / "opt/arby-patch-agent",
                self.root,
            )

    def test_symlinked_parent_rejected(self):
        actual = self.root / "actual"
        actual.mkdir()

        parent = self.root / "opt"
        parent.symlink_to(actual, target_is_directory=True)

        with self.assertRaises(RuntimeError):
            installer.require_secure_ancestors(
                self.root / "opt/arby-patch-agent",
                self.root,
            )

    def test_regular_file_parent_rejected(self):
        parent = self.root / "opt"
        parent.write_text("not a directory")

        with self.assertRaises(RuntimeError):
            installer.require_secure_ancestors(
                self.root / "opt/arby-patch-agent",
                self.root,
            )

    def test_missing_parent_allowed(self):
        installer.require_secure_ancestors(
            self.root / "opt/arby-patch-agent",
            self.root,
        )


if __name__ == "__main__":
    unittest.main()
