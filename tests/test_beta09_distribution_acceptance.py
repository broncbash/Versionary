"""Offline distribution acceptance: never installs to / or contacts servers."""
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, INSTALLER / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("beta09_builder", "build-agent-package.py")
validator = load("beta09_validator", "validate-package.py")
installer = load("beta09_installer", "install-files.py")


class DistributionAcceptance(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="versionary-beta09-")
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name)
        self.package = self.workspace / "versionary-agent.tar.gz"
        self.root = self.workspace / "isolated-root"
        self.root.mkdir(mode=0o700)

    def build(self):
        builder.build(self.package)

    def install(self):
        installer.install(self.package, self.root)

    def test_reproducible_distribution(self):
        self.build()
        first = self.package.read_bytes()
        self.build()
        self.assertEqual(first, self.package.read_bytes())
        self.assertEqual(validator.validate(self.package), 13)

    def test_clean_install_is_isolated_and_inactive(self):
        self.build()
        self.install()
        app = self.root / "opt/versionary-agent"
        active = app / "agent"
        state = self.root / "var/lib/versionary-agent"
        self.assertTrue(active.is_symlink())
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)
        self.assertTrue(os.readlink(active).startswith("releases/"))
        for name, contents in validator.load_modules(self.package).items():
            self.assertEqual((active / name).read_bytes(), contents)
        self.assertFalse((self.root / "etc/systemd/system/versionary-agent.service").exists())
        self.assertFalse((self.root / "etc/systemd/system/versionary-agent.timer").exists())
        self.assertFalse((self.root / "etc/versionary-agent/config.json").exists())

    def test_reinstall_preserves_private_state(self):
        self.build()
        self.install()
        active = self.root / "opt/versionary-agent/agent"
        state = self.root / "var/lib/versionary-agent"
        marker = state / "preserve-me"
        marker.write_bytes(b"existing-private-state")
        marker.chmod(0o600)
        before = os.readlink(active)
        self.install()
        self.assertEqual(os.readlink(active), before)
        self.assertEqual(marker.read_bytes(), b"existing-private-state")
        self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o600)

    def test_invalid_package_rejected_before_install(self):
        self.build()
        data = self.package.read_bytes()
        self.package.write_bytes(b"NOT-GZIP" + data[8:])
        with self.assertRaises(Exception):
            self.install()
        self.assertFalse((self.root / "opt/versionary-agent").exists())

    def test_installed_cli_help_runs_offline(self):
        self.build()
        self.install()
        result = subprocess.run(
            [sys.executable, "-m", "agent", "--help"],
            cwd=self.root / "opt/versionary-agent",
            capture_output=True, text=True, timeout=30, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("report", result.stdout)


if __name__ == "__main__":
    unittest.main()
