"""Verify that reinstalling preserves persistent agent state."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/install-files.py"
PACKAGE = ROOT / "installer/dist/versionary-agent.tar.gz"


class AgentReinstallationTests(unittest.TestCase):

    def install(self, root):
        result = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                str(PACKAGE),
                "--root",
                str(root),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + "\n" + result.stderr,
        )

    def test_reinstallation_preserves_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            self.install(root)

            state = root / "var/lib/versionary-agent"
            identity = state / "identity.json"
            credential = state / "credential.json"

            identity.write_text(json.dumps({
                "agent_id": "12345678-1234-4234-8234-123456789abc",
                "hostname": "test-agent",
                "platform": "arch",
            }))

            credential.write_text(json.dumps({
                "token": "TEST-ONLY-NOT-A-REAL-CREDENTIAL"
            }))

            os.chmod(identity, 0o600)
            os.chmod(credential, 0o600)

            before = {
                path.name: hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (identity, credential)
            }

            agent = root / "opt/versionary-agent/agent"
            release_before = os.readlink(agent)

            self.install(root)

            after = {
                path.name: hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (identity, credential)
            }

            self.assertEqual(before, after)
            self.assertEqual(os.readlink(agent), release_before)
            self.assertEqual(state.stat().st_mode & 0o777, 0o700)
            self.assertEqual(identity.stat().st_mode & 0o777, 0o600)
            self.assertEqual(credential.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
