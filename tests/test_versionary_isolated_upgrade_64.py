"""Versionary isolated upgrade and recovery acceptance."""

import importlib.util
from pathlib import Path
import subprocess
import sys
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
    "versionary_upgrade_test_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_upgrade_test_engine",
)


def make_payloads(version):
    return {
        name: f"version-{version}:{name}".encode()
        for name in coordinator.MODES
    }


class UpgradeTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-upgrade64-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = make_payloads(1)
        self.new = make_payloads(2)

        coordinator.install_payloads_isolated(
            self.root, self.old
        )

    def test_real_root_forbidden(self):
        with self.assertRaises(ValueError):
            upgrade.apply("/", self.old, self.new)

    def test_identical_upgrade_is_noop(self):
        result = upgrade.apply(
            self.root, self.old, self.old
        )
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "clear",
        )

    def test_complete_upgrade_requires_review(self):
        result = upgrade.apply(
            self.root, self.old, self.new
        )
        self.assertEqual(
            result["updated"], len(self.old)
        )
        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "recovery_required",
        )
        for name, data in self.new.items():
            self.assertEqual(
                (self.root / name).read_bytes(), data
            )

    def test_interrupted_upgrade_restores_original(self):
        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.old, self.new,
                fail_after=2,
            )

        result = upgrade.recover_to_old(self.root)
        self.assertEqual(result["restored"], 2)

        review = upgrade.review_complete(self.root)
        self.assertEqual(
            review["status"], "original_restored"
        )

        for name, data in self.old.items():
            self.assertEqual(
                (self.root / name).read_bytes(), data
            )

    def test_restart_can_recover_interrupted_upgrade(self):
        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.old, self.new,
                fail_after=1,
            )

        script = """
import importlib.util
import sys
spec = importlib.util.spec_from_file_location(
    "fresh_upgrade", sys.argv[1]
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.recover_to_old(sys.argv[2])
assert result["status"] == "restored_review_required"
assert module.review_complete(sys.argv[2])["status"] == "original_restored"
print("FRESH_PROCESS_RECOVERY=PASS")
"""
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                script,
                str(
                    INSTALLER
                    / "versionary-agent-isolated-upgrade.py"
                ),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertIn(
            "FRESH_PROCESS_RECOVERY=PASS",
            result.stdout,
        )

    def test_pending_upgrade_blocks_second_upgrade(self):
        upgrade.apply(self.root, self.old, self.new)

        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.new, self.old
            )

    def test_unexpected_content_blocks_recovery(self):
        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.old, self.new,
                fail_after=1,
            )

        target = self.root / next(iter(sorted(self.old)))
        target.write_bytes(b"unexpected-user-change")

        with self.assertRaises(ValueError):
            upgrade.recover_to_old(self.root)

        self.assertEqual(
            target.read_bytes(),
            b"unexpected-user-change",
        )

    def test_private_state_preserved(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True, mode=0o700)

        credential = state / "credential.json"
        credential.write_bytes(b"private-credential")
        credential.chmod(0o600)

        upgrade.apply(self.root, self.old, self.new)

        self.assertEqual(
            credential.read_bytes(),
            b"private-credential",
        )

    def test_preexisting_conflict_blocks_upgrade(self):
        target = self.root / next(iter(self.old))
        target.write_bytes(b"unrecognized-content")

        with self.assertRaises(ValueError):
            upgrade.apply(
                self.root, self.old, self.new
            )

        self.assertEqual(
            upgrade.inspect_pending(self.root)["status"],
            "clear",
        )


if __name__ == "__main__":
    unittest.main()
