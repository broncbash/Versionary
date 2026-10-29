"""Regression tests for concurrent release activation."""

import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_concurrency", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseConcurrency(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('original')\n",
            "identity.py": b"IDENTITY = True\n",
        }

        self.identifier = atomic.stage_release(
            self.app, self.modules
        )

    def test_existing_activation_symlink_not_overwritten(self):
        occupied = self.app / ".agent-next"
        occupied.symlink_to("important-target")

        atomic.activate_release(self.app, self.identifier)

        self.assertEqual(
            occupied.readlink().as_posix(),
            "important-target",
        )
        self.assertEqual(
            (self.app / "agent").readlink().as_posix(),
            f"releases/{self.identifier}/agent",
        )

    def test_parallel_activation_does_not_corrupt_release(self):
        errors = []
        barrier = threading.Barrier(2)

        original_sync = atomic.sync_directory

        def coordinated_sync(path):
            if Path(path) == self.app:
                try:
                    barrier.wait(timeout=2)
                except threading.BrokenBarrierError:
                    pass

            return original_sync(path)

        def worker():
            try:
                atomic.activate_release(
                    self.app, self.identifier
                )
            except Exception as error:
                errors.append(error)

        with patch.object(
            atomic,
            "sync_directory",
            side_effect=coordinated_sync,
        ):
            threads = [
                threading.Thread(target=worker)
                for _ in range(2)
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join(timeout=5)

        self.assertTrue(
            (self.app / "agent").is_symlink()
        )

        self.assertEqual(
            (self.app / "agent").readlink().as_posix(),
            f"releases/{self.identifier}/agent",
        )

        self.assertFalse(
            (self.app / ".agent-next").exists()
        )

        self.assertLessEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
