"""Versionary beta fresh-install execution acceptance tests."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "installer/versionary-agent-beta-fresh-install.py"
)

spec = importlib.util.spec_from_file_location(
    "versionary_beta_fresh_install_76",
    SOURCE,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


PAYLOADS = {
    "opt/versionary-agent/versionary_agent_cli.py": b"agent",
    "etc/versionary-agent/config.json": b"config",
    "etc/versionary-agent/ca.crt": b"certificate",
    "etc/systemd/system/versionary-agent.service": b"service",
    "etc/systemd/system/versionary-agent.timer": b"timer",
}


class FreshInstallExecutionTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.root = Path(self.temporary.name)
        os.chmod(self.root, 0o700)

    def execute(self, authorization=None):
        if authorization is None:
            authorization = module.AUTHORIZATION

        return module.execute_prepared(
            self.root,
            PAYLOADS,
            authorization,
        )

    def test_authorization_required(self):
        with self.assertRaises(PermissionError):
            self.execute("")

        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_authorization_rejected(self):
        with self.assertRaises(PermissionError):
            self.execute("yes")

        self.assertEqual(list(self.root.iterdir()), [])

    def test_real_root_rejected(self):
        with self.assertRaises(ValueError):
            module.execute_prepared(
                "/",
                PAYLOADS,
                module.AUTHORIZATION,
            )

    def test_isolated_fresh_install(self):
        result = self.execute()

        self.assertEqual(
            result["status"],
            "isolated_fresh_install_complete",
        )

        self.assertEqual(result["created"], 5)
        self.assertEqual(result["preserved"], 0)
        self.assertTrue(result["installation_performed"])

        self.assertFalse(
            result["real_system_installation_enabled"]
        )

        self.assertFalse(result["services_activated"])
        self.assertFalse(result["enrollment_performed"])
        self.assertFalse(result["upgrades_supported"])

        for relative, expected in PAYLOADS.items():
            self.assertEqual(
                (self.root / relative).read_bytes(),
                expected,
            )

    def test_reinstallation_refused(self):
        self.execute()

        with self.assertRaises(RuntimeError):
            self.execute()

        for relative, expected in PAYLOADS.items():
            self.assertEqual(
                (self.root / relative).read_bytes(),
                expected,
            )

    def test_conflicting_file_preserved(self):
        target = (
            self.root
            / "etc/versionary-agent/config.json"
        )

        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing")
        os.chmod(target, 0o600)

        with self.assertRaises(ValueError):
            self.execute()

        self.assertEqual(target.read_bytes(), b"existing")

    def test_pending_upgrade_blocks_execution(self):
        marker = (
            self.root
            / ".versionary-upgrade-transaction"
        )

        marker.mkdir()

        with self.assertRaises(RuntimeError):
            self.execute()

        self.assertTrue(marker.exists())

    def test_pending_install_journal_blocks_execution(self):
        marker = (
            self.root
            / ".versionary-install-journal.json"
        )

        marker.write_text("pending")
        os.chmod(marker, 0o600)

        with self.assertRaises(
            (RuntimeError, ValueError)
        ):
            self.execute()

        self.assertTrue(marker.exists())

    def test_no_services_or_enrollment(self):
        self.execute()

        self.assertFalse(
            (self.root / "var/lib/versionary-agent/credential.json")
            .exists()
        )

        self.assertFalse(
            (self.root / "run/systemd/system")
            .exists()
        )

    def test_successful_install_removes_journal(self):
        self.execute()

        self.assertFalse(
            (self.root / ".versionary-install-journal.json")
            .exists()
        )

    def test_preview_does_not_write(self):
        with patch.object(
            module,
            "prepare",
            return_value=(
                self.root,
                PAYLOADS,
                {"status": "ready_for_isolated_fresh_install"},
            ),
        ):
            result = module.run(
                self.root,
                "distribution",
                "https://example.test",
                "ca",
            )

        self.assertEqual(
            result["status"],
            "ready_for_isolated_fresh_install",
        )

        self.assertEqual(list(self.root.iterdir()), [])

    def test_execution_requires_authorization_before_prepare(self):
        with patch.object(module, "prepare") as prepare:
            with self.assertRaises(PermissionError):
                module.run(
                    self.root,
                    "distribution",
                    "https://example.test",
                    "ca",
                    execute=True,
                )

            prepare.assert_not_called()

    def test_preview_rejects_execution_authorization(self):
        with self.assertRaises(ValueError):
            module.run(
                self.root,
                "distribution",
                "https://example.test",
                "ca",
                authorization=module.AUTHORIZATION,
            )


if __name__ == "__main__":
    unittest.main()
