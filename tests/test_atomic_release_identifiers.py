"""Security tests for atomic release identifiers."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_identifiers", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseIdentifiers(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "versionary-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('hello')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.identifier = atomic.stage_release(
            self.app, self.modules
        )

    def test_valid_identifier_accepted(self):
        atomic.activate_release(
            self.app, self.identifier
        )

        self.assertTrue(
            (self.app / "agent").is_symlink()
        )

    def test_parent_traversal_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            atomic.activate_release(
                self.app, "../escape"
            )

    def test_absolute_identifier_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            atomic.activate_release(
                self.app, "/tmp/escape"
            )

    def test_nested_identifier_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            atomic.activate_release(
                self.app, "nested/release"
            )

    def test_empty_identifier_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            atomic.activate_release(
                self.app, ""
            )

    def test_non_hex_identifier_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            atomic.activate_release(
                self.app, "not-a-release-id"
            )


if __name__ == "__main__":
    unittest.main()
