"""Permanent integration tests for the isolated Versionary agent installer.

Exercises real installer helpers against disposable filesystem roots.
No networking, registration, systemd activation, or production changes.
"""

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/install-agent-offline.py"
CERT_GENERATOR = ROOT / "installer/generate-certificates.py"
BUNDLE = (
    ROOT / "installer/dist/"
    "versionary-agent-distribution-26l.tar.gz"
)
SERVER = "https://versionary.example.test"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OfflineIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not BUNDLE.is_file():
            raise RuntimeError(
                "Build the verified 26L distribution before "
                "running integration tests"
            )

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(
            prefix="versionary-integration-"
        )
        self.addCleanup(self.workspace.cleanup)

        self.base = Path(self.workspace.name)
        self.root = self.base / "installation"
        self.root.mkdir(mode=0o700)

        self.certificates = self.base / "certificates"

        result = subprocess.run(
            [
                sys.executable,
                str(CERT_GENERATOR),
                "--hostname",
                "versionary.example.test",
                "--output",
                str(self.certificates),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            result.returncode, 0,
            result.stdout + result.stderr,
        )

        self.ca = self.certificates / "ca.crt"
        self.assertTrue(self.ca.is_file())

    def execute(self):
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--root",
                str(self.root),
                "--distribution",
                str(BUNDLE),
                "--server",
                SERVER,
                "--ca-cert",
                str(self.ca),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def successful_install(self):
        result = self.execute()
        self.assertEqual(
            result.returncode, 0,
            result.stdout + result.stderr,
        )
        return result

    def installed_paths(self):
        return [
            self.root / "opt/versionary-agent/agent",
            self.root / "opt/versionary-agent/versionary_agent_cli.py",
            self.root / "etc/versionary-agent/ca.crt",
            self.root / "etc/versionary-agent/config.json",
            self.root / "etc/systemd/system/versionary-agent.service",
            self.root / "etc/systemd/system/versionary-agent.timer",
        ]

    def test_complete_installation(self):
        self.successful_install()

        for path in self.installed_paths():
            self.assertTrue(path.exists(), str(path))

        state = self.root / "var/lib/versionary-agent"

        self.assertEqual(
            stat.S_IMODE(state.stat().st_mode),
            0o700,
        )

        self.assertFalse((state / "identity.json").exists())
        self.assertFalse((state / "credential.json").exists())

        config = json.loads(
            (
                self.root /
                "etc/versionary-agent/config.json"
            ).read_text()
        )

        self.assertEqual(config["server"], SERVER)
        self.assertEqual(
            config["ca_cert"],
            "/etc/versionary-agent/ca.crt",
        )

        wants = self.root / "etc/systemd/system"
        self.assertFalse(
            (wants / "timers.target.wants").exists()
        )
        self.assertFalse(
            (wants / "multi-user.target.wants").exists()
        )

    def test_identical_reinstallation(self):
        self.successful_install()

        before = {
            str(path): digest(path)
            for path in self.installed_paths()
            if path.is_file()
        }

        release = os.readlink(
            self.root / "opt/versionary-agent/agent"
        )

        self.successful_install()

        after = {
            str(path): digest(path)
            for path in self.installed_paths()
            if path.is_file()
        }

        self.assertEqual(before, after)
        self.assertEqual(
            release,
            os.readlink(
                self.root / "opt/versionary-agent/agent"
            ),
        )

    def test_existing_agent_state_survives_reinstall(self):
        self.successful_install()

        state = self.root / "var/lib/versionary-agent"
        identity = state / "identity.json"
        credential = state / "credential.json"

        # Synthetic local fixtures, never real credentials.
        identity.write_text('{"fixture":"identity"}\n')
        credential.write_text('{"fixture":"credential"}\n')

        identity.chmod(0o600)
        credential.chmod(0o600)

        before = (
            identity.read_bytes(),
            credential.read_bytes(),
        )

        self.successful_install()

        self.assertEqual(identity.read_bytes(), before[0])
        self.assertEqual(credential.read_bytes(), before[1])
        self.assertEqual(
            stat.S_IMODE(credential.stat().st_mode),
            0o600,
        )

    def test_conflicting_cli_is_not_overwritten(self):
        self.successful_install()

        cli = (
            self.root /
            "opt/versionary-agent/versionary_agent_cli.py"
        )

        cli.write_text("existing conflicting CLI\n")
        cli.chmod(0o644)

        before = cli.read_bytes()

        result = self.execute()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(cli.read_bytes(), before)

    def test_conflicting_ca_is_not_overwritten(self):
        self.successful_install()

        ca = self.root / "etc/versionary-agent/ca.crt"
        ca.write_text("existing conflicting CA\n")

        before = ca.read_bytes()

        result = self.execute()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(ca.read_bytes(), before)

    def test_recovery_after_interrupted_installation(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "versionary_offline_recovery",
            INSTALLER,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        original = module.run_helper
        interrupted = False

        def fail_before_systemd(script, *args):
            nonlocal interrupted

            if script == "install-systemd.py":
                interrupted = True
                raise subprocess.CalledProcessError(
                    42,
                    [script],
                )

            return original(script, *args)

        with patch.object(
            module,
            "run_helper",
            side_effect=fail_before_systemd,
        ):
            with self.assertRaises(
                subprocess.CalledProcessError
            ):
                module.install(
                    self.root,
                    BUNDLE,
                    SERVER,
                    self.ca,
                )

        self.assertTrue(interrupted)

        # Earlier successful stages remain; no fake rollback.
        self.assertTrue(
            (
                self.root /
                "etc/versionary-agent/config.json"
            ).exists()
        )

        state = self.root / "var/lib/versionary-agent"

        self.assertFalse(
            (state / "credential.json").exists()
        )

        self.assertFalse(
            (
                self.root /
                "etc/systemd/system/versionary-agent.service"
            ).exists()
        )

        # Re-running must safely complete the remaining stages.
        self.successful_install()

        for path in self.installed_paths():
            self.assertTrue(path.exists(), str(path))

    def test_recovery_preserves_preexisting_state(self):
        self.successful_install()

        state = self.root / "var/lib/versionary-agent"
        credential = state / "credential.json"

        credential.write_text(
            '{"fixture":"preserve-during-failure"}\n'
        )
        credential.chmod(0o600)

        before = credential.read_bytes()

        cli = (
            self.root /
            "opt/versionary-agent/versionary_agent_cli.py"
        )

        original_cli = cli.read_bytes()
        cli.write_text("temporary conflicting CLI\n")

        failed = self.execute()

        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(credential.read_bytes(), before)

        # Restore only our synthetic conflicting fixture.
        cli.write_bytes(original_cli)

        self.successful_install()

        self.assertEqual(credential.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
