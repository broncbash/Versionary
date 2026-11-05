import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "installer/"
    "versionary-agent-beta-full-fresh-install.py"
)
BUNDLE = (
    ROOT / "installer/dist/"
    "versionary-agent-distribution-26l.tar.gz"
)
GENERATOR = ROOT / "installer/generate-certificates.py"
SERVER = "https://versionary.example.test"

spec = importlib.util.spec_from_file_location(
    "versionary_full77", SCRIPT
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FullFreshInstallTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "root"
        self.root.mkdir(mode=0o700)

    def test_rejects_real_root(self):
        with self.assertRaises(ValueError):
            module.inspect("/")

    def test_empty_root_ready(self):
        result = module.inspect(self.root)
        self.assertEqual(result["module_count"], 13)
        self.assertFalse(result["installation_performed"])

    def test_preview_does_not_modify_root(self):
        module.inspect(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_existing_agent(self):
        app = self.root / "opt/versionary-agent"
        app.mkdir(parents=True)
        (app / "agent").symlink_to("releases/test/agent")
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_rejects_existing_state(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True)
        (state / "identity.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_rejects_unknown_app_content(self):
        app = self.root / "opt/versionary-agent"
        app.mkdir(parents=True)
        (app / "unknown").write_text("preserve")
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_rejects_pending_journal(self):
        (self.root / ".versionary-install-journal.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_rejects_upgrade_journal(self):
        (self.root / ".versionary-upgrade-transaction").mkdir()
        with self.assertRaises(RuntimeError):
            module.inspect(self.root)

    def test_requires_authorization_before_prepare(self):
        with self.assertRaises(PermissionError):
            module.run(
                self.root, BUNDLE, SERVER, "unused",
                execute=True,
            )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_full_real_isolated_integration(self):
        if not BUNDLE.is_file():
            self.skipTest("Verified distribution unavailable")

        certs = self.base / "certificates"
        generated = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--hostname",
                "versionary.example.test",
                "--output",
                str(certs),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            generated.returncode, 0,
            generated.stdout + generated.stderr,
        )

        ca = certs / "ca.crt"

        preview = module.run(
            self.root, BUNDLE, SERVER, ca
        )
        self.assertFalse(preview["installation_performed"])
        self.assertEqual(list(self.root.iterdir()), [])

        result = module.run(
            self.root, BUNDLE, SERVER, ca,
            execute=True,
            authorization=module.AUTHORIZATION,
        )
        self.assertEqual(
            result["status"],
            "isolated_full_fresh_install_complete",
        )

        agent = (
            self.root / "opt/versionary-agent/agent"
        )
        self.assertTrue(agent.is_symlink())

        names = {
            entry.name
            for entry in agent.iterdir()
            if entry.is_file()
        }
        self.assertEqual(len(names), 13)

        config = json.loads(
            (
                self.root /
                "etc/versionary-agent/config.json"
            ).read_text()
        )
        self.assertEqual(config["server"], SERVER)

        self.assertTrue(
            (
                self.root /
                "etc/systemd/system/versionary-agent.timer"
            ).is_file()
        )

        self.assertFalse(
            (
                self.root /
                "var/lib/versionary-agent/credential.json"
            ).exists()
        )

        with self.assertRaises(
            (RuntimeError, ValueError)
        ):
            module.run(
                self.root, BUNDLE, SERVER, ca,
                execute=True,
                authorization=module.AUTHORIZATION,
            )


if __name__ == "__main__":
    unittest.main()
