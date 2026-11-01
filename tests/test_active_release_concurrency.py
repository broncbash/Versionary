"""Adversarial tests for active-release verification concurrency checks."""

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
    "versionary_concurrency_integrity",
)
atomic = load(
    "atomic-release.py",
    "versionary_concurrency_atomic",
)


class ReleaseConcurrencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        self.root = Path(temporary.name) / "root"
        self.root.mkdir(mode=0o700)
        self.app = self.root / "opt/versionary-agent"
        self.app.mkdir(parents=True)

        self.modules = {
            "__main__.py": b"print('safe')\n",
            "identity.py": b"IDENTITY = True\n",
        }
        self.identifier = atomic.release_id(self.modules)
        self.release = self.app / "releases" / self.identifier / "agent"
        self.release.mkdir(parents=True)

        for name, content in self.modules.items():
            (self.release / name).write_bytes(content)

        (self.app / "agent").symlink_to(
            f"releases/{self.identifier}/agent"
        )

    def test_unchanged_release_passes(self):
        result = integrity.verify_integrity(self.root)
        self.assertTrue(result["integrity_verified"])
        self.assertFalse(result["rollback_authorized"])

    def test_module_modified_after_read_is_rejected(self):
        original = integrity.read_file
        changed = False

        def modifying_read(parent, name):
            nonlocal changed
            data = original(parent, name)
            if name == "identity.py" and not changed:
                changed = True
                (self.release / "__main__.py").write_bytes(b"TAMPERED\n")
            return data

        with patch.object(integrity, "read_file", side_effect=modifying_read):
            with self.assertRaises((RuntimeError, ValueError)):
                integrity.verify_integrity(self.root)

    def test_module_replaced_after_read_is_rejected(self):
        original = integrity.read_file
        changed = False

        def replacing_read(parent, name):
            nonlocal changed
            data = original(parent, name)
            if name == "identity.py" and not changed:
                changed = True
                target = self.release / "__main__.py"
                target.unlink()
                target.write_bytes(self.modules["__main__.py"])
            return data

        with patch.object(integrity, "read_file", side_effect=replacing_read):
            with self.assertRaises((RuntimeError, ValueError)):
                integrity.verify_integrity(self.root)

    def test_release_directory_replacement_is_rejected(self):
        original = integrity.check_directory_identity
        changed = False

        def replacing_directory(parent, name, fd):
            nonlocal changed
            if name == "agent" and not changed:
                changed = True
                moved = self.release.with_name("agent-old")
                self.release.rename(moved)
                self.release.mkdir()
                for module, data in self.modules.items():
                    (self.release / module).write_bytes(data)
            return original(parent, name, fd)

        with patch.object(
            integrity,
            "check_directory_identity",
            side_effect=replacing_directory,
        ):
            with self.assertRaises(RuntimeError):
                integrity.verify_integrity(self.root)

    def test_persistent_extra_entry_is_rejected(self):
        original = integrity.check_file_unchanged
        changed = False

        def adding_entry(parent, name, expected):
            nonlocal changed
            if not changed:
                changed = True
                (self.release / "unexpected.py").write_bytes(b"EXTRA\n")
            return original(parent, name, expected)

        with patch.object(
            integrity,
            "check_file_unchanged",
            side_effect=adding_entry,
        ):
            with self.assertRaises(RuntimeError):
                integrity.verify_integrity(self.root)


if __name__ == "__main__":
    unittest.main()
