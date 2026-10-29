"""Regression tests for locked release installation transactions."""

import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_transaction", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseTransaction(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.modules = {
            "__main__.py": b"print('installed')\n",
            "identity.py": b"IDENTITY = True\n",
        }

    def test_transaction_stages_and_activates(self):
        identifier = atomic.install_release(
            self.app, self.modules
        )

        self.assertEqual(
            identifier,
            atomic.release_id(self.modules),
        )

        self.assertEqual(
            (self.app / "agent").readlink().as_posix(),
            f"releases/{identifier}/agent",
        )

    def test_transaction_preserves_active_on_staging_failure(self):
        original = atomic.install_release(
            self.app, self.modules
        )

        updated = {
            "__main__.py": b"print('updated')\n",
        }

        with patch.object(
            atomic,
            "stage_release",
            side_effect=OSError("Simulated staging failure"),
        ):
            with self.assertRaises(OSError):
                atomic.install_release(self.app, updated)

        self.assertEqual(
            (self.app / "agent").readlink().as_posix(),
            f"releases/{original}/agent",
        )

    def test_reinstall_rejects_tampered_source_without_switching(self):
        original = atomic.install_release(self.app, self.modules)
        active = self.app / "agent"
        (active / "identity.py").write_bytes(b"TAMPERED\\n")
        before = active.readlink()
        with self.assertRaises(RuntimeError):
            atomic.install_release(self.app, self.modules)
        self.assertEqual(active.readlink(), before)
        self.assertEqual(original, atomic.release_id(self.modules))

    def test_reinstall_rejects_unsafe_cache_without_switching(self):
        original = atomic.install_release(self.app, self.modules)
        active = self.app / "agent"
        (active / "__pycache__").symlink_to(self.app)
        with self.assertRaises(RuntimeError):
            atomic.install_release(self.app, self.modules)
        self.assertEqual(active.readlink().as_posix(),
                         f"releases/{original}/agent")

    def test_failed_upgrade_activation_preserves_previous_release(self):
        original = atomic.install_release(self.app, self.modules)
        updated = {"__main__.py": b"print('updated')\\n"}
        with patch.object(atomic, "activate_release",
                          side_effect=RuntimeError("simulated activation failure")):
            with self.assertRaises(RuntimeError):
                atomic.install_release(self.app, updated)
        self.assertEqual((self.app / "agent").readlink().as_posix(),
                         f"releases/{original}/agent")
        self.assertEqual((self.app / "agent/identity.py").read_bytes(),
                         self.modules["identity.py"])

    def test_reinstall_rejects_extra_cache_file_without_switching(self):
        original = atomic.install_release(self.app, self.modules)
        active = self.app / "agent"
        cache = active / "__pycache__"
        cache.mkdir()
        (cache / "unexpected.txt").write_text("unsafe")
        with self.assertRaises(RuntimeError):
            atomic.install_release(self.app, self.modules)
        self.assertEqual(active.readlink().as_posix(),
                         f"releases/{original}/agent")

    def test_transaction_holds_lock_through_activation(self):
        entered = threading.Event()
        release = threading.Event()
        errors = []

        original_activate = atomic.activate_release

        def blocked_activate(app, identifier):
            entered.set()

            if not release.wait(timeout=3):
                raise RuntimeError("Activation test timed out")

            return original_activate(app, identifier)

        def worker():
            try:
                atomic.install_release(self.app, self.modules)
            except Exception as error:
                errors.append(error)

        with patch.object(
            atomic,
            "activate_release",
            side_effect=blocked_activate,
        ):
            thread = threading.Thread(target=worker)
            thread.start()

            try:
                self.assertTrue(
                    entered.wait(timeout=2),
                    "Transaction never reached activation",
                )

                # A second attempt must not acquire the lock
                # while activation is paused.
                import fcntl
                import os

                fd = os.open(
                    self.app / ".install.lock",
                    os.O_RDWR | os.O_NOFOLLOW,
                )

                try:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(
                            fd,
                            fcntl.LOCK_EX | fcntl.LOCK_NB,
                        )
                finally:
                    os.close(fd)
            finally:
                release.set()
                thread.join(timeout=4)

        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
