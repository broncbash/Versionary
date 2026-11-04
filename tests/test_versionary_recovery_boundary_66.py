"""Shared installation and upgrade recovery boundary."""

import importlib.util
from pathlib import Path
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
    "versionary_boundary_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_boundary_upgrade",
)


def payloads(version):
    return {
        name: f"version-{version}:{name}".encode()
        for name in coordinator.MODES
    }


class RecoveryBoundaryTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-boundary66-"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = payloads(1)
        self.new = payloads(2)

    def test_pending_upgrade_blocks_identical_install(self):
        coordinator.install_payloads_isolated(
            self.root, self.old
        )
        upgrade.apply(self.root, self.old, self.new)

        with self.assertRaisesRegex(
            RuntimeError, "Pending upgrade"
        ):
            coordinator.install_payloads_isolated(
                self.root, self.new
            )

    def test_interrupted_upgrade_blocks_install(self):
        coordinator.install_payloads_isolated(
            self.root, self.old
        )

        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.old, self.new,
                fail_after=1,
            )

        with self.assertRaisesRegex(
            RuntimeError, "Pending upgrade"
        ):
            coordinator.install_payloads_isolated(
                self.root, self.old
            )

    def test_symlinked_upgrade_marker_blocks_install(self):
        target = self.root / "unrelated"
        target.mkdir()

        marker = (
            self.root / ".versionary-upgrade-transaction"
        )
        marker.symlink_to(target, target_is_directory=True)

        with self.assertRaisesRegex(
            RuntimeError, "Pending upgrade"
        ):
            coordinator.install_payloads_isolated(
                self.root, self.old
            )

    def test_normal_install_still_works(self):
        result = coordinator.install_payloads_isolated(
            self.root, self.old
        )
        self.assertEqual(
            result["created"], len(self.old)
        )

    def test_pending_install_blocks_upgrade(self):
        with self.assertRaises(RuntimeError):
            coordinator.install_payloads_isolated(
                self.root, self.old, fail_after=0
            )

        with self.assertRaises(RuntimeError):
            upgrade.apply(
                self.root, self.old, self.new
            )


if __name__ == "__main__":
    unittest.main()
