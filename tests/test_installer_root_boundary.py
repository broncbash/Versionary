"""Installation-root and ancestor boundary security tests."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "arby_root_boundary_installer",
    ROOT / "installer/install-files.py",
)

installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TestRootBoundary(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_group_writable_root_rejected(self):
        self.root.chmod(0o775)

        with self.assertRaises(RuntimeError):
            installer.require_secure_install_root(self.root)

    def test_world_writable_root_rejected(self):
        self.root.chmod(0o777)

        with self.assertRaises(RuntimeError):
            installer.require_secure_install_root(self.root)

    def test_safe_root_accepted(self):
        self.root.chmod(0o700)
        installer.require_secure_install_root(self.root)

    def test_symlinked_root_rejected(self):
        link = self.root.parent / (
            self.root.name + "-link"
        )
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink)

        with self.assertRaises(RuntimeError):
            installer.require_secure_install_root(link)

    def test_wrong_owner_root_rejected(self):
        self.root.chmod(0o700)

        with patch.object(
            installer.os, "geteuid",
            return_value=os.geteuid() + 1,
        ):
            with self.assertRaises(RuntimeError):
                installer.require_secure_install_root(self.root)

    def test_missing_parent_then_existing_file_rejected(self):
        (self.root / "opt").mkdir()
        (self.root / "opt" / "blocked").write_text("file")

        with self.assertRaises(RuntimeError):
            installer.require_secure_ancestors(
                self.root / "opt/blocked/child/agent",
                self.root,
            )


if __name__ == "__main__":
    unittest.main()
