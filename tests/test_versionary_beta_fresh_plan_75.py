"""Controlled beta fresh-install readiness regression tests."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "installer/versionary-agent-beta-fresh-plan.py"
)

spec = importlib.util.spec_from_file_location(
    "versionary_beta_fresh_plan_75",
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


class FreshInstallPlanTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.root = Path(self.temporary.name)
        os.chmod(self.root, 0o700)

    def inspect(self, payloads=None):
        return module.inspect_fresh_root(
            self.root,
            PAYLOADS if payloads is None else payloads,
        )

    def test_empty_root_is_ready(self):
        result = self.inspect()

        self.assertEqual(
            result["status"],
            "ready_for_isolated_fresh_install",
        )
        self.assertEqual(result["payload_count"], 5)
        self.assertTrue(result["fresh_install_only"])
        self.assertFalse(result["upgrades_supported"])
        self.assertFalse(
            result["real_system_installation_enabled"]
        )
        self.assertFalse(result["installation_performed"])

    def test_does_not_create_payload_files(self):
        self.inspect()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_real_system_root(self):
        with self.assertRaises(ValueError):
            module.inspect_fresh_root("/", PAYLOADS)

    def test_rejects_unexpected_payload(self):
        with self.assertRaises(ValueError):
            self.inspect({"unexpected": b"data"})

    def test_rejects_empty_payload(self):
        payloads = dict(PAYLOADS)
        payloads[
            "etc/versionary-agent/config.json"
        ] = b""

        with self.assertRaises(ValueError):
            self.inspect(payloads)

    def test_rejects_existing_matching_file(self):
        target = (
            self.root
            / "etc/versionary-agent/config.json"
        )
        target.parent.mkdir(parents=True)
        target.write_bytes(b"config")
        os.chmod(target, 0o600)

        with self.assertRaisesRegex(
            RuntimeError, "Fresh installation"
        ):
            self.inspect()

        self.assertEqual(target.read_bytes(), b"config")

    def test_rejects_conflicting_existing_file(self):
        target = (
            self.root
            / "etc/versionary-agent/config.json"
        )
        target.parent.mkdir(parents=True)
        target.write_bytes(b"different")
        os.chmod(target, 0o600)

        with self.assertRaises(ValueError):
            self.inspect()

        self.assertEqual(target.read_bytes(), b"different")

    def test_rejects_pending_upgrade(self):
        marker = (
            self.root
            / ".versionary-upgrade-transaction"
        )
        marker.mkdir()

        with self.assertRaisesRegex(
            RuntimeError, "Pending upgrade"
        ):
            self.inspect()

    def test_rejects_pending_installation_journal(self):
        marker = (
            self.root
            / ".versionary-install-journal.json"
        )
        marker.write_text("unresolved", encoding="utf-8")
        os.chmod(marker, 0o600)

        with self.assertRaises(
            (RuntimeError, ValueError)
        ):
            self.inspect()

        self.assertTrue(marker.exists())

    def test_rejects_writable_root(self):
        os.chmod(self.root, 0o777)

        with self.assertRaises(ValueError):
            self.inspect()

    def test_existing_safe_parent_directories_allowed(self):
        directory = self.root / "etc/versionary-agent"
        directory.mkdir(parents=True)
        os.chmod(directory, 0o700)

        result = self.inspect()

        self.assertEqual(
            result["status"],
            "ready_for_isolated_fresh_install",
        )
        self.assertIn(
            "etc/versionary-agent",
            result["existing_directories"],
        )


if __name__ == "__main__":
    unittest.main()
