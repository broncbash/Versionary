"""Tests for the non-installing Versionary system beta preflight."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "installer/versionary-agent-system-preflight.py"

spec = importlib.util.spec_from_file_location(
    "versionary_agent_system_preflight",
    SOURCE,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SystemPreflightTests(unittest.TestCase):

    def test_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                module.validate_regular_file(
                    Path(temporary) / "missing", "Test", 1024
                )

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            original.write_bytes(b"safe")
            link = root / "link"
            link.symlink_to(original)

            with self.assertRaises(ValueError):
                module.validate_regular_file(link, "Test", 1024)

    def test_rejects_world_writable_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "test"
            target.write_bytes(b"data")
            target.chmod(0o666)

            with self.assertRaises(ValueError):
                module.validate_regular_file(target, "Test", 1024)

    def test_accepts_secure_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "test"
            target.write_bytes(b"data")
            target.chmod(0o644)

            self.assertEqual(
                module.validate_regular_file(
                    target, "Test", 1024
                ),
                target,
            )

    def test_rejects_empty_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "empty"
            target.touch()

            with self.assertRaises(ValueError):
                module.validate_regular_file(target, "Test", 1024)

    def test_rejects_oversized_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "large"
            target.write_bytes(b"x" * 17)

            with self.assertRaises(ValueError):
                module.validate_regular_file(target, "Test", 16)

    def test_rejects_unsupported_platform(self):
        with patch.object(
            module.platform, "system", return_value="Windows"
        ):
            with self.assertRaises(ValueError):
                module.validate_platform()

    def test_production_not_approved(self):
        self.assertNotIn(
            "os.system(",
            SOURCE.read_text(),
        )
        self.assertNotIn(
            "subprocess.run(",
            SOURCE.read_text(),
        )
        self.assertNotIn(
            "install_release(",
            SOURCE.read_text(),
        )


if __name__ == "__main__":
    unittest.main()
