"""Verify private state permissions during agent installation."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer/install-files.py"
ARCHIVE = ROOT / "installer/dist/arby-patch-agent.tar.gz"


spec = importlib.util.spec_from_file_location(
    "arby_private_state_installer", INSTALLER
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PrivateStateTests(unittest.TestCase):

    def test_rejects_existing_0755_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "var/lib/arby-patch-agent"
            state.mkdir(parents=True)
            os.chmod(state, 0o755)

            with self.assertRaisesRegex(
                RuntimeError, "permissions 0700"
            ):
                installer.install(ARCHIVE, root)

            self.assertEqual(
                state.stat().st_mode & 0o777, 0o755
            )

            agent = root / "opt/arby-patch-agent/agent"
            self.assertFalse(agent.exists())
            self.assertFalse(agent.is_symlink())

    def test_accepts_existing_0700_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "var/lib/arby-patch-agent"
            state.mkdir(parents=True)
            os.chmod(state, 0o700)

            installer.install(ARCHIVE, root)

            self.assertEqual(
                state.stat().st_mode & 0o777, 0o700
            )

            agent = root / "opt/arby-patch-agent/agent"
            self.assertTrue(agent.is_symlink())


if __name__ == "__main__":
    unittest.main()
