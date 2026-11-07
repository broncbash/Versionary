"""Prevent passing a raw agent archive to the guided installer."""
import unittest
import hashlib
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentInstallerHandoffTests(unittest.TestCase):
    def test_verified_distribution_is_passed_to_guided_installer(self):
        script = (ROOT / "install-versionary-agent.sh").read_text()
        self.assertIn('cp -- "$RAW" "$STAGED"', script)
        self.assertIn('build-agent-distribution.py', script)
        self.assertIn('--output "$DIST"', script)
        self.assertIn('--verify "$DIST"', script)
        self.assertIn('set -- --distribution "$DIST"', script)
        self.assertNotIn(
            'set -- --distribution "$DIR/versionary-$TAG-agent.tar.gz"',
            script,
        )

    def test_raw_archive_is_wrapped_and_preserved(self):
        raw = ROOT / "installer/dist/versionary-agent.tar.gz"
        builder = ROOT / "installer/build-agent-distribution.py"
        self.assertTrue(raw.is_file(), "Raw agent archive missing")

        original_hash = hashlib.sha256(raw.read_bytes()).hexdigest()

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "distribution.tar.gz"

            subprocess.run(
                [sys.executable, str(builder), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(builder), "--verify", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )

            with tarfile.open(output, "r:gz") as archive:
                self.assertEqual(
                    set(archive.getnames()),
                    {
                        "manifest.json",
                        "versionary-agent.tar.gz",
                        "versionary_agent_cli.py",
                    },
                )

                wrapped_raw = archive.extractfile(
                    "versionary-agent.tar.gz"
                ).read()

            self.assertEqual(wrapped_raw, raw.read_bytes())

        self.assertEqual(
            hashlib.sha256(raw.read_bytes()).hexdigest(),
            original_hash,
        )

    def test_distribution_is_verified_before_install(self):
        script = (ROOT / "install-versionary-agent.sh").read_text()
        verify = script.index('--verify "$DIST"')
        guided = script.index('as_root bash source/installer/versionary-agent-guided-install.sh')
        self.assertLess(verify, guided)


if __name__ == "__main__":
    unittest.main()
