"""Versionary beta readiness CLI acceptance tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "installer/versionary-beta-readiness.py"

spec = importlib.util.spec_from_file_location(
    "versionary_readiness86", SOURCE
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(
            prefix="versionary-readiness86-"
        )
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_relative_root_rejected(self):
        with self.assertRaises(ValueError):
            module.check_root("relative")

    def test_system_root_requires_explicit_flag(self):
        with self.assertRaises(ValueError):
            module.check_root("/")

    def test_system_root_explicit_audit_allowed(self):
        self.assertEqual(
            module.check_root("/", True), Path("/")
        )

    def test_symlink_root_rejected(self):
        link = self.root.parent / (
            self.root.name + "-link"
        )
        link.symlink_to(
            self.root, target_is_directory=True
        )
        self.addCleanup(link.unlink)
        with self.assertRaises(ValueError):
            module.check_root(link)

    def test_invalid_distribution_blocks_readiness(self):
        result = module.report(
            self.root,
            self.root / "missing.tar.gz",
            "https://versionary.example.test",
            self.root / "missing.crt",
        )
        self.assertFalse(result["ready_for_review"])
        self.assertFalse(result["deployment_authorized"])
        self.assertFalse(result["installation_performed"])

    def test_system_audit_never_authorizes_install(self):
        with patch.object(
            module, "check_root", return_value=Path("/")
        ):
            result = module.report(
                "/", "missing", "https://example.test",
                "missing", allow_system=True
            )
        self.assertIn(
            "real_system_installation_not_implemented",
            result["blockers"],
        )
        self.assertFalse(result["deployment_authorized"])

    def test_sha256(self):
        file = self.root / "sample"
        file.write_bytes(b"abc")
        self.assertEqual(
            module.digest(file),
            "ba7816bf8f01cfea414140de5dae2223"
            "b00361a396177a9cb410ff61f20015ad",
        )

    def test_no_install_or_service_controls(self):
        source = SOURCE.read_text()
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("systemctl", source)
        self.assertNotIn("installer.run(", source)

if __name__ == "__main__":
    unittest.main()
