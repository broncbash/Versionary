"""Deterministic regression test for shared activation symlink races."""

import importlib.util
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "installer/atomic-release.py"

spec = importlib.util.spec_from_file_location(
    "arby_atomic_race", SCRIPT
)
atomic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atomic)


class TestAtomicReleaseRace(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.app = Path(self.temp.name) / "arby-patch-agent"
        self.app.mkdir()

        self.first = atomic.stage_release(
            self.app,
            {"__main__.py": b"FIRST = True\n"},
        )

        self.second = atomic.stage_release(
            self.app,
            {"__main__.py": b"SECOND = True\n"},
        )

    def test_parallel_activation_does_not_steal_temp_symlink(self):
        first_ready = threading.Event()
        second_finished = threading.Event()

        errors = []
        real_replace = os.replace

        def controlled_replace(source, destination):
            if (
                Path(source).name.startswith(".agent-next-")
                and threading.current_thread().name == "first"
            ):
                first_ready.set()

                if not second_finished.wait(timeout=5):
                    raise RuntimeError("Second activation did not finish")

            return real_replace(source, destination)

        def activate_first():
            try:
                atomic.activate_release(self.app, self.first)
            except Exception as error:
                errors.append(("first", error))

        def activate_second():
            try:
                if not first_ready.wait(timeout=5):
                    raise RuntimeError("First activation did not reach replace")

                atomic.activate_release(self.app, self.second)
            except Exception as error:
                errors.append(("second", error))
            finally:
                second_finished.set()

        with patch.object(
            atomic.os,
            "replace",
            side_effect=controlled_replace,
        ):
            first_thread = threading.Thread(
                target=activate_first,
                name="first",
            )

            second_thread = threading.Thread(
                target=activate_second,
                name="second",
            )

            first_thread.start()
            second_thread.start()

            first_thread.join(timeout=7)
            second_thread.join(timeout=7)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())

        self.assertEqual(
            errors,
            [],
            f"Concurrent activation errors: {errors}",
        )

        active = self.app / "agent"

        self.assertTrue(active.is_symlink())
        self.assertIn(
            active.readlink().as_posix(),
            {
                f"releases/{self.first}/agent",
                f"releases/{self.second}/agent",
            },
        )


if __name__ == "__main__":
    unittest.main()
