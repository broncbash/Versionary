"""Security and behavior tests for atomic release staging."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_release_security", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseSecurity(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('hello')\n",
            "identity.py": b"IDENTITY = True\n",
        }

    def test_stage_creates_complete_release(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        agent = (
            self.app / "releases" / identifier / "agent"
        )

        self.assertTrue(agent.is_dir())
        self.assertEqual(
            {p.name for p in agent.iterdir()},
            set(self.modules),
        )

        for name, data in self.modules.items():
            self.assertEqual(
                (agent / name).read_bytes(), data
            )

    def test_repeated_stage_is_idempotent(self):
        first = atomic.stage_release(
            self.app, self.modules
        )
        second = atomic.stage_release(
            self.app, self.modules
        )

        self.assertEqual(first, second)

    def test_activation_switches_symlink(self):
        first = atomic.stage_release(
            self.app, self.modules
        )
        atomic.activate_release(self.app, first)

        self.assertTrue(
            (self.app / "agent").is_symlink()
        )

        updated = dict(self.modules)
        updated["identity.py"] = b"IDENTITY = False\n"

        second = atomic.stage_release(
            self.app, updated
        )
        atomic.activate_release(self.app, second)

        self.assertEqual(
            os.readlink(self.app / "agent"),
            f"releases/{second}/agent",
        )

    def test_existing_release_tampering_rejected(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        target = (
            self.app / "releases"
            / identifier / "agent/identity.py"
        )
        target.write_bytes(b"tampered")

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_symlinked_releases_directory_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()

        (self.app / "releases").symlink_to(
            outside, target_is_directory=True
        )

        with self.assertRaises(RuntimeError):
            atomic.stage_release(self.app, self.modules)

    def test_legacy_agent_directory_rejected(self):
        (self.app / "agent").mkdir()

        identifier = atomic.stage_release(
            self.app, self.modules
        )

        with self.assertRaises(RuntimeError):
            atomic.activate_release(self.app, identifier)

    def test_occupied_activation_path_rejected(self):
        identifier = atomic.stage_release(
            self.app, self.modules
        )

        occupied = self.app / ".agent-next"
        occupied.write_text("occupied")

        atomic.activate_release(self.app, identifier)

        self.assertEqual(occupied.read_text(), "occupied")
        self.assertTrue((self.app / "agent").is_symlink())
        self.assertEqual(
            (self.app / "agent").readlink().as_posix(),
            f"releases/{identifier}/agent",
        )

    def test_unsafe_module_name_rejected(self):
        with self.assertRaises(ValueError):
            atomic.stage_release(
                self.app,
                {"../escape.py": b"unsafe"},
            )


if __name__ == "__main__":
    unittest.main()
