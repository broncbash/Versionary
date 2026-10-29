"""Production ownership policy for ARBY PATCH AGENT installer."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "installer/dist/arby-patch-agent.tar.gz"

spec = importlib.util.spec_from_file_location(
    "arby_production_ownership_installer",
    ROOT / "installer/install-files.py",
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TestProductionOwnership(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_nonroot_production_install_rejected(self):
        with patch.object(installer.os, "geteuid", return_value=1000):
            with self.assertRaises((PermissionError, RuntimeError)):
                installer.require_production_root(Path("/"))

    def test_root_production_install_accepted(self):
        with patch.object(installer.os, "geteuid", return_value=0):
            installer.require_production_root(Path("/"))

    def test_isolated_test_root_accepted(self):
        with patch.object(installer.os, "geteuid", return_value=1000):
            installer.require_production_root(self.root)

    def test_group_writable_app_rejected(self):
        app = self.root / "opt/arby-patch-agent"
        app.mkdir(parents=True)
        app.chmod(0o775)

        with self.assertRaises(RuntimeError):
            installer.require_secure_app_directory(app)

    def test_world_writable_app_rejected(self):
        app = self.root / "opt/arby-patch-agent"
        app.mkdir(parents=True)
        app.chmod(0o777)

        with self.assertRaises(RuntimeError):
            installer.require_secure_app_directory(app)

    def test_safe_app_accepted(self):
        app = self.root / "opt/arby-patch-agent"
        app.mkdir(parents=True)
        app.chmod(0o755)

        installer.require_secure_app_directory(app)

    def test_symlinked_app_rejected(self):
        actual = self.root / "actual"
        actual.mkdir()

        app = self.root / "app"
        app.symlink_to(actual, target_is_directory=True)

        with self.assertRaises(RuntimeError):
            installer.require_secure_app_directory(app)


if __name__ == "__main__":
    unittest.main()
