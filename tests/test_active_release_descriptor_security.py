"""Descriptor-based active-release verification security tests."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "installer"


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integrity = load(
    "active-release-integrity.py",
    "versionary_descriptor_security",
)
atomic = load(
    "atomic-release.py",
    "versionary_descriptor_atomic",
)


class DescriptorSecurityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name) / "root"
        self.root.mkdir(mode=0o700)

        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.modules = {
            "__main__.py": b"print('safe')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.identifier = atomic.release_id(self.modules)
        self.release = (
            self.app / "releases" / self.identifier / "agent"
        )
        self.release.mkdir(parents=True)

        for name, data in self.modules.items():
            (self.release / name).write_bytes(data)

        self.pointer = self.app / "agent"
        self.pointer.symlink_to(
            f"releases/{self.identifier}/agent"
        )

    def test_valid_release_uses_descriptors(self):
        result = integrity.verify_integrity(self.root)
        self.assertTrue(result["integrity_verified"])
        self.assertTrue(result["descriptor_based"])
        self.assertFalse(result["rollback_authorized"])

    def test_symlinked_module_rejected(self):
        module = self.release / "identity.py"
        module.unlink()
        module.symlink_to(self.release / "__main__.py")

        with self.assertRaises((OSError, RuntimeError, ValueError)):
            integrity.verify_integrity(self.root)

    def test_symlinked_cache_entry_rejected(self):
        cache = self.release / "__pycache__"
        cache.mkdir()
        (cache / "identity.pyc").symlink_to(
            self.release / "identity.py"
        )

        with self.assertRaises((OSError, RuntimeError, ValueError)):
            integrity.verify_integrity(self.root)

    def test_release_directory_symlink_rejected(self):
        original = self.release
        moved = original.with_name("agent-original")
        original.rename(moved)
        original.symlink_to(moved)

        with self.assertRaises((OSError, RuntimeError, ValueError)):
            integrity.verify_integrity(self.root)

    def test_pointer_replacement_during_inspection_rejected(self):
        original_read_pointer = integrity.read_pointer
        calls = 0

        def changing_pointer(app_fd):
            nonlocal calls
            calls += 1

            if calls == 2:
                self.pointer.unlink()
                self.pointer.symlink_to(
                    f"releases/{self.identifier}/agent"
                )

            return original_read_pointer(app_fd)

        with patch.object(
            integrity,
            "read_pointer",
            side_effect=changing_pointer,
        ):
            with self.assertRaises(ValueError):
                integrity.verify_integrity(self.root)

    def test_module_swap_before_open_rejected(self):
        original_open = os.open
        swapped = False

        def swapping_open(path, flags, *args, **kwargs):
            nonlocal swapped

            if (
                path == "identity.py"
                and "dir_fd" in kwargs
                and not swapped
            ):
                swapped = True
                module = self.release / "identity.py"
                module.unlink()
                module.symlink_to(self.release / "__main__.py")

            return original_open(path, flags, *args, **kwargs)

        with patch.object(
            integrity.os,
            "open",
            side_effect=swapping_open,
        ):
            with self.assertRaises((OSError, RuntimeError, ValueError)):
                integrity.verify_integrity(self.root)

    def test_absent_release_is_not_verified(self):
        self.pointer.unlink()
        result = integrity.verify_integrity(self.root)
        self.assertEqual(result["status"], "absent")
        self.assertFalse(result["integrity_verified"])


if __name__ == "__main__":
    unittest.main()
