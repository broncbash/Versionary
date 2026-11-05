"""End-to-end isolated Versionary beta workflow acceptance."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "installer/versionary-agent-beta-install-workflow.py"
BUNDLE = BASE / "installer/dist/versionary-agent-distribution-26l.tar.gz"
GENERATOR = BASE / "installer/generate-certificates.py"
SERVER = "https://versionary.example.test"

spec = importlib.util.spec_from_file_location(
    "versionary_beta81", SCRIPT
)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class WorkflowIntegrationTests(unittest.TestCase):

    def setUp(self):
        if not BUNDLE.is_file():
            self.skipTest("Distribution unavailable")

        temp = tempfile.TemporaryDirectory(
            prefix="versionary-beta81-"
        )
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / "isolated-root"
        self.root.mkdir(mode=0o700)

        certs = self.base / "certificates"
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--hostname", "versionary.example.test",
                "--output", str(certs),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            result.returncode, 0,
            result.stdout + result.stderr,
        )
        self.ca = certs / "ca.crt"

    def test_preview_then_install_then_refuse_reinstall(self):
        preview = workflow.prepare(
            self.root, BUNDLE, SERVER, self.ca
        )
        self.assertFalse(preview["installation_performed"])
        self.assertEqual(list(self.root.iterdir()), [])

        result = workflow.execute(
            self.root,
            BUNDLE,
            SERVER,
            self.ca,
            workflow.AUTHORIZATION,
        )

        self.assertEqual(
            result["installation_result"]["status"],
            "isolated_full_fresh_install_complete",
        )
        self.assertFalse(result["services_activated"])
        self.assertFalse(result["enrollment_performed"])

        agent = self.root / "opt/versionary-agent/agent"
        self.assertTrue(agent.is_symlink())

        modules = [
            p for p in agent.iterdir() if p.is_file()
        ]
        self.assertEqual(len(modules), 13)

        config = json.loads(
            (
                self.root / "etc/versionary-agent/config.json"
            ).read_text()
        )
        self.assertEqual(config["server"], SERVER)

        self.assertTrue(
            (
                self.root /
                "etc/systemd/system/versionary-agent.timer"
            ).is_file()
        )

        with self.assertRaises((RuntimeError, ValueError)):
            workflow.execute(
                self.root,
                BUNDLE,
                SERVER,
                self.ca,
                workflow.AUTHORIZATION,
            )

    def test_refuses_existing_identity_without_modification(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True)
        identity = state / "identity.json"
        identity.write_text('{"preserve": true}\n')

        with self.assertRaises((RuntimeError, ValueError)):
            workflow.execute(
                self.root,
                BUNDLE,
                SERVER,
                self.ca,
                workflow.AUTHORIZATION,
            )

        self.assertEqual(
            identity.read_text(),
            '{"preserve": true}\n',
        )


if __name__ == "__main__":
    unittest.main()
