"""Verify release integrity before activation."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_integrity", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseIntegrity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('hello')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.identifier = atomic.stage_release(
            self.app, self.modules
        )

        self.agent = (
            self.app / "releases"
            / self.identifier / "agent"
        )

    def test_valid_release_activates(self):
        atomic.activate_release(
            self.app, self.identifier
        )

        self.assertTrue(
            (self.app / "agent").is_symlink()
        )

    def test_modified_module_blocks_activation(self):
        module = self.agent / "identity.py"
        module.write_bytes(b"IDENTITY = False\n")

        with self.assertRaises(RuntimeError):
            atomic.activate_release(
                self.app, self.identifier
            )

        self.assertFalse(
            (self.app / "agent").is_symlink()
        )

    def test_missing_module_blocks_activation(self):
        (self.agent / "identity.py").unlink()

        with self.assertRaises(RuntimeError):
            atomic.activate_release(
                self.app, self.identifier
            )

    def test_extra_module_blocks_activation(self):
        (self.agent / "unexpected.py").write_bytes(
            b"UNEXPECTED = True\n"
        )

        with self.assertRaises(RuntimeError):
            atomic.activate_release(
                self.app, self.identifier
            )

    def test_empty_release_blocks_activation(self):
        for module in self.agent.iterdir():
            module.unlink()

        with self.assertRaises(RuntimeError):
            atomic.activate_release(
                self.app, self.identifier
            )


if __name__ == "__main__":
    unittest.main()
