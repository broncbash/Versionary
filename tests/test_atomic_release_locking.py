"""Cross-process installer locking regression tests."""

import importlib.util
import multiprocessing
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_locking", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


def hold_lock(app, ready, release):
    with atomic.install_lock(app):
        ready.set()
        if not release.wait(timeout=5):
            raise RuntimeError("Lock holder timed out")


def wait_for_lock(app, acquired):
    with atomic.install_lock(app):
        acquired.set()


class TestAtomicReleaseLocking(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

    def test_lock_is_exclusive_across_processes(self):
        ctx = multiprocessing.get_context("fork")
        ready = ctx.Event()
        release = ctx.Event()
        acquired = ctx.Event()

        holder = ctx.Process(
            target=hold_lock,
            args=(self.app, ready, release),
        )
        waiter = ctx.Process(
            target=wait_for_lock,
            args=(self.app, acquired),
        )

        try:
            holder.start()
            self.assertTrue(
                ready.wait(timeout=3),
                "First process did not acquire lock",
            )

            waiter.start()

            self.assertFalse(
                acquired.wait(timeout=0.2),
                "Second process bypassed installer lock",
            )

            release.set()

            self.assertTrue(
                acquired.wait(timeout=3),
                "Second process never acquired released lock",
            )
        finally:
            release.set()

            for process in (holder, waiter):
                if process.pid is not None:
                    process.join(timeout=3)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=3)

        self.assertEqual(holder.exitcode, 0)
        self.assertEqual(waiter.exitcode, 0)

    def test_lock_released_after_exception(self):
        with self.assertRaises(ValueError):
            with atomic.install_lock(self.app):
                raise ValueError("Simulated installer failure")

        with atomic.install_lock(self.app):
            self.assertTrue(
                (self.app / ".install.lock").is_file()
            )

    def test_symlinked_lock_file_rejected(self):
        lock = self.app / ".install.lock"
        lock.symlink_to("unexpected-target")

        with self.assertRaises((OSError, RuntimeError)):
            with atomic.install_lock(self.app):
                pass

        self.assertTrue(lock.is_symlink())


if __name__ == "__main__":
    unittest.main()
