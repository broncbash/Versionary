"""Regression tests for unexpected release filesystem entries."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_tampering", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseTampering(unittest.TestCase):

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

    def test_extra_file_rejected(self):
        (self.agent / "unexpected.py").write_text(
            "UNEXPECTED = True\n"
        )

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_extra_symlink_rejected(self):
        (self.agent / "unexpected.py").symlink_to(
            "/etc/passwd"
        )

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_expected_module_replaced_by_symlink_rejected(self):
        target = self.agent / "identity.py"
        target.unlink()
        target.symlink_to("/etc/passwd")

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_extra_directory_rejected(self):
        (self.agent / "unexpected").mkdir()

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)


if __name__ == "__main__":
    unittest.main()
