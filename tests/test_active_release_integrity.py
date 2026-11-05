"""Security regression tests for read-only active release integrity."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "installer"


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integrity = load(
    "active-release-integrity.py",
    "versionary_integrity_tests",
)
atomic = load(
    "atomic-release.py",
    "versionary_integrity_test_atomic",
)


class ActiveReleaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name) / "root"
        self.root.mkdir(mode=0o700)

        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.modules = {
            "__main__.py": b"print('versionary')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.identifier = atomic.release_id(self.modules)
        self.release = (
            self.app / "releases" / self.identifier / "agent"
        )
        self.release.mkdir(parents=True)

        for name, data in self.modules.items():
            (self.release / name).write_bytes(data)

        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )

    def test_valid_release(self):
        result = integrity.verify_integrity(self.root)
        self.assertTrue(result["integrity_verified"])
        self.assertFalse(result["authenticity_verified"])
        self.assertFalse(result["provenance_verified"])
        self.assertFalse(result["rollback_authorized"])
        self.assertEqual(result["module_count"], 2)

    def test_tampered_module_rejected(self):
        (self.release / "identity.py").write_bytes(b"TAMPERED\n")
        with self.assertRaises(ValueError):
            integrity.verify_integrity(self.root)

    def test_missing_module_rejected(self):
        (self.release / "identity.py").unlink()
        with self.assertRaises(ValueError):
            integrity.verify_integrity(self.root)

    def test_unexpected_file_rejected(self):
        (self.release / "unexpected.txt").write_text("bad")
        with self.assertRaises(ValueError):
            integrity.verify_integrity(self.root)

    def test_symlinked_module_rejected(self):
        target = self.release / "identity.py"
        target.unlink()
        target.symlink_to(self.release / "__main__.py")
        with self.assertRaises(RuntimeError):
            integrity.verify_integrity(self.root)

    def test_hardlinked_module_rejected(self):
        target = self.release / "identity.py"
        target.unlink()
        target.hardlink_to(self.release / "__main__.py")
        with self.assertRaises(RuntimeError):
            integrity.verify_integrity(self.root)

    def test_empty_release_rejected(self):
        for entry in self.release.iterdir():
            entry.unlink()
        with self.assertRaises(ValueError):
            integrity.verify_integrity(self.root)

    def test_unsafe_cache_rejected(self):
        (self.release / "__pycache__").symlink_to(self.app)
        with self.assertRaises(RuntimeError):
            integrity.verify_integrity(self.root)

    def test_safe_cache_accepted(self):
        cache = self.release / "__pycache__"
        cache.mkdir()
        (cache / "identity.cpython-314.pyc").write_bytes(b"cache")
        result = integrity.verify_integrity(self.root)
        self.assertTrue(result["integrity_verified"])

    def test_absent_release(self):
        (self.app / "agent").unlink()
        result = integrity.verify_integrity(self.root)
        self.assertFalse(result["integrity_verified"])
        self.assertEqual(result["status"], "absent")


if __name__ == "__main__":
    unittest.main()
