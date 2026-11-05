"""Unified Versionary installation-kit regression tests."""

import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "installer"


class UnifiedInstallationKitTests(unittest.TestCase):

    def run_script(self, name, *arguments):
        return subprocess.run(
            [sys.executable, str(INSTALLER / name), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_unified_builder_help(self):
        result = self.run_script(
            "build-unified-installation-kit.py", "--help"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--server-archive", result.stdout)
        self.assertIn("--server-manifest", result.stdout)
        self.assertIn("--output", result.stdout)

    def test_agent_launcher_help(self):
        result = self.run_script("install-versionary-agent", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--execute-disposable", result.stdout)

    def test_server_launcher_help(self):
        result = self.run_script("install-versionary-server", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--archive", result.stdout)

    def test_missing_release_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "kit.tar.gz"

            result = self.run_script(
                "build-unified-installation-kit.py",
                "--server-archive", str(root / "missing.tar.gz"),
                "--server-manifest", str(root / "missing.json"),
                "--output", str(output),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "kit.tar.gz"
            output.write_bytes(b"preserve")

            result = self.run_script(
                "build-unified-installation-kit.py",
                "--server-archive", str(root / "missing.tar.gz"),
                "--server-manifest", str(root / "missing.json"),
                "--output", str(output),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b"preserve")

    def test_base_kit_contains_agent_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "kit.tar.gz"

            result = self.run_script(
                "build-installation-kit.py",
                "--output", str(output),
            )

            self.assertEqual(
                result.returncode,
                0,
                result.stdout + result.stderr,
            )

            with tarfile.open(output, "r:gz") as archive:
                names = set(archive.getnames())

            prefix = "versionary-install-kit/"

            for name in (
                "installer/atomic-release.py",
                "installer/systemd/versionary-agent.service",
                "installer/systemd/versionary-agent.timer",
                "installer/install-versionary-agent",
            ):
                with self.subTest(name=name):
                    self.assertIn(prefix + name, names)


if __name__ == "__main__":
    unittest.main()
