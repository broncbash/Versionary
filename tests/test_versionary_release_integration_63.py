"""Versionary release kit and isolated lifecycle acceptance."""

import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"

REQUIRED = {
    "installer/versionary-agent-isolated-coordinator.py",
    "installer/versionary-agent-isolated-upgrade.py",
    "installer/versionary-agent-system-preflight.py",
    "installer/versionary-agent-system-content.py",
    "installer/versionary-agent-system-conflicts.py",
    "installer/versionary-agent-system-transaction.py",
    "installer/versionary-agent-system-journal.py",
    "installer/versionary-agent-system-recovery.py",
    "installer/install-agent-cli.py",
    "installer/install-ca.py",
    "agent/config.py",
    "installer/systemd/versionary-agent.service",
    "installer/systemd/versionary-agent.timer",
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator = load(
    INSTALLER / "versionary-agent-isolated-coordinator.py",
    "versionary_release_integration_coordinator",
)

recovery = load(
    INSTALLER / "versionary-agent-system-recovery.py",
    "versionary_release_integration_recovery",
)


def payloads(suffix=b""):
    return {
        name: b"versionary-release-test:" + name.encode() + suffix
        for name in coordinator.MODES
    }


class ReleaseKitIntegrationTests(unittest.TestCase):

    def test_packaged_installer_dependency_closure(self):
        with tempfile.TemporaryDirectory(
            prefix="versionary-kit-integration-"
        ) as temp:
            temp = Path(temp)
            kit = temp / "kit.tar.gz"

            subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER / "build-installation-kit.py"),
                    "--output",
                    str(kit),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with tarfile.open(kit, "r:gz") as archive:
                members = archive.getmembers()
                names = [member.name for member in members]

                self.assertEqual(len(names), len(set(names)))
                self.assertTrue(all(m.isfile() for m in members))

                for required in REQUIRED:
                    self.assertIn(
                        "versionary-install-kit/" + required,
                        names,
                    )

                for member in members:
                    self.assertNotIn("..", Path(member.name).parts)
                    self.assertFalse(member.name.startswith("/"))

                for member in members:
                    target = temp / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(
                        archive.extractfile(member).read()
                    )

            packaged = temp / "versionary-install-kit"
            module = load(
                packaged
                / "installer/versionary-agent-isolated-coordinator.py",
                "versionary_packaged_coordinator",
            )

            self.assertEqual(
                set(module.MODES),
                set(coordinator.MODES),
            )

            # Exercise packaged coordinator using only packaged
            # installer modules, not the repository checkout.
            isolated = temp / "isolated-root"
            isolated.mkdir(mode=0o700)
            data = {
                name: b"packaged:" + name.encode()
                for name in module.MODES
            }
            result = module.install_payloads_isolated(
                isolated, data
            )
            self.assertEqual(result["created"], len(data))

            again = module.install_payloads_isolated(
                isolated, data
            )
            self.assertEqual(again["created"], 0)
            self.assertEqual(
                again["preserved"], len(data)
            )


class RecoveryAndUpgradeTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-recovery-63-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_simulated_restart_blocks_pending_journal(self):
        data = payloads()

        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, data, fail_after=0
            )

        # A fresh Python process must independently detect the
        # persistent recovery marker.
        script = """
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "fresh_recovery", sys.argv[1]
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.inspect_pending(Path(sys.argv[2]))
assert result["status"] == "recovery_required"
print("RESTART_RECOVERY_BLOCK=PASS")
"""
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                script,
                str(
                    INSTALLER
                    / "versionary-agent-system-recovery.py"
                ),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn(
            "RESTART_RECOVERY_BLOCK=PASS",
            result.stdout,
        )

        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, data
            )

    def test_conflicting_upgrade_preserves_all_files(self):
        original = payloads()
        coordinator.install_payloads_isolated(
            self.root, original
        )

        changed = payloads(b":new-release")

        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                self.root, changed
            )

        for name, expected in original.items():
            self.assertEqual(
                (self.root / name).read_bytes(),
                expected,
            )

    def test_identical_reinstall_preserves_existing_state(self):
        data = payloads()
        coordinator.install_payloads_isolated(
            self.root, data
        )

        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True, mode=0o700)
        credential = state / "credential.json"
        credential.write_bytes(b"private-test-credential")
        credential.chmod(0o600)

        result = coordinator.install_payloads_isolated(
            self.root, data
        )

        self.assertEqual(result["created"], 0)
        self.assertEqual(
            credential.read_bytes(),
            b"private-test-credential",
        )

    def test_recovery_clear_requires_absent_payloads(self):
        data = payloads()
        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, data, fail_after=0
            )

        target = self.root / next(iter(data))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[next(iter(data))])

        with self.assertRaises(RuntimeError):
            recovery.review_and_clear(
                self.root, data
            )

        self.assertTrue(target.exists())

    def test_real_root_remains_forbidden(self):
        with self.assertRaises(ValueError):
            coordinator.install_payloads_isolated(
                Path("/"), payloads()
            )


if __name__ == "__main__":
    unittest.main()
