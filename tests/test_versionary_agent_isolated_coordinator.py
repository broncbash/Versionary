"""Integration tests for the isolated installation coordinator."""

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, INSTALLER / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    "versionary-agent-isolated-coordinator.py",
    "versionary_isolated_coordinator_tests",
)


def payloads():
    return {
        name: ("versionary-test:" + name).encode()
        for name in coordinator.MODES
    }


class IsolatedCoordinatorTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-coordinator-test-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = payloads()

    def test_rejects_real_system_root(self):
        with self.assertRaises(ValueError):
            coordinator.validate_root("/")

    def test_rejects_relative_root(self):
        with self.assertRaises(ValueError):
            coordinator.validate_root("relative-root")

    def test_rejects_symlinked_root(self):
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            coordinator.validate_root(link)

    def test_rejects_world_writable_root(self):
        os.chmod(self.root, 0o777)
        with self.assertRaises(ValueError):
            coordinator.validate_root(self.root)

    def test_rejects_incomplete_inventory(self):
        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, {"unexpected": b"data"}
            )

    def test_rejects_empty_payload(self):
        data = dict(self.data)
        first = next(iter(data))
        data[first] = b""
        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, data
            )

    def test_installs_all_expected_files(self):
        result = coordinator.install_payloads_isolated(
            self.root, self.data
        )
        self.assertEqual(result["created"], len(self.data))
        self.assertEqual(result["preserved"], 0)

        for name, expected in self.data.items():
            path = self.root / name
            self.assertEqual(path.read_bytes(), expected)
            self.assertEqual(
                stat.S_IMODE(path.stat().st_mode),
                coordinator.MODES[name],
            )

    def test_idempotent_reinstallation(self):
        coordinator.install_payloads_isolated(
            self.root, self.data
        )
        result = coordinator.install_payloads_isolated(
            self.root, self.data
        )
        self.assertEqual(result["created"], 0)
        self.assertEqual(
            result["preserved"], len(self.data)
        )

    def test_existing_conflict_preserved(self):
        target = self.root / next(iter(self.data))
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing-user-content")

        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, self.data
            )

        self.assertEqual(
            target.read_bytes(), b"existing-user-content"
        )

    def test_symlinked_destination_rejected(self):
        target = self.root / next(iter(self.data))
        target.parent.mkdir(parents=True)
        outside = self.root / "outside"
        outside.write_bytes(b"preserve")
        target.symlink_to(outside)

        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, self.data
            )

        self.assertEqual(outside.read_bytes(), b"preserve")

    def test_failure_retains_review_journal(self):
        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, self.data, fail_after=1
            )

        recovery = load(
            "versionary-agent-system-recovery.py",
            "versionary_coordinator_recovery_test",
        )

        pending = recovery.inspect_pending(self.root)
        self.assertEqual(
            pending["status"], "recovery_required"
        )

        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, self.data
            )

    def test_review_clear_after_rollback(self):
        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, self.data, fail_after=0
            )

        recovery = load(
            "versionary-agent-system-recovery.py",
            "versionary_coordinator_clear_test",
        )

        result = recovery.review_and_clear(
            self.root, self.data
        )
        self.assertEqual(result["status"], "cleared")
        self.assertEqual(result["files_removed"], 0)

        installed = coordinator.install_payloads_isolated(
            self.root, self.data
        )
        self.assertEqual(
            installed["created"], len(self.data)
        )

    def test_rejects_private_state_directory_conflict(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True)
        state.chmod(0o755)

        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, self.data
            )

    def test_does_not_modify_existing_unrelated_file(self):
        unrelated = self.root / "user-data.txt"
        unrelated.write_bytes(b"keep this")

        coordinator.install_payloads_isolated(
            self.root, self.data
        )

        self.assertEqual(
            unrelated.read_bytes(), b"keep this"
        )


if __name__ == "__main__":
    unittest.main()
