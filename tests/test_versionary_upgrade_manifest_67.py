"""Security checks for isolated upgrade manifests."""

import importlib.util
import json
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
    "versionary_manifest67_coordinator",
)

upgrade = load(
    "versionary-agent-isolated-upgrade.py",
    "versionary_manifest67_upgrade",
)


class ManifestSecurityTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="versionary-manifest67-"
        )
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name)

        self.old = {
            name: f"old:{name}".encode()
            for name in coordinator.MODES
        }

        self.new = {
            name: f"new:{name}".encode()
            for name in coordinator.MODES
        }

        coordinator.install_payloads_isolated(
            self.root, self.old
        )

        upgrade.apply(
            self.root, self.old, self.new
        )

        self.manifest_path = (
            self.root
            / ".versionary-upgrade-transaction"
            / "manifest.json"
        )

    def modify(self, change):
        manifest = json.loads(
            self.manifest_path.read_text()
        )
        change(manifest)
        self.manifest_path.write_text(
            json.dumps(manifest, sort_keys=True)
        )
        self.manifest_path.chmod(0o600)

    def verify_rejected_without_changes(self):
        before = {
            name: (self.root / name).read_bytes()
            for name in self.new
        }

        with self.assertRaises(ValueError):
            upgrade.recover_to_old(self.root)

        for name, content in before.items():
            self.assertEqual(
                (self.root / name).read_bytes(),
                content,
            )

    def test_path_traversal_rejected(self):
        def change(manifest):
            name = sorted(manifest["files"])[0]
            manifest["files"][name]["old"] = "../outside"

        self.modify(change)
        self.verify_rejected_without_changes()

    def test_duplicate_snapshot_reference_rejected(self):
        def change(manifest):
            names = sorted(manifest["files"])
            manifest["files"][names[1]]["old"] = (
                manifest["files"][names[0]]["old"]
            )

        self.modify(change)
        self.verify_rejected_without_changes()

    def test_swapped_snapshot_identity_rejected(self):
        def change(manifest):
            names = sorted(manifest["files"])
            first = manifest["files"][names[0]]
            second = manifest["files"][names[1]]

            first["old"], second["old"] = (
                second["old"], first["old"]
            )

        self.modify(change)
        self.verify_rejected_without_changes()

    def test_valid_manifest_still_recovers(self):
        result = upgrade.recover_to_old(self.root)

        self.assertEqual(
            result["restored"], len(self.old)
        )

        self.assertEqual(
            upgrade.review_complete(self.root)["status"],
            "original_restored",
        )


if __name__ == "__main__":
    unittest.main()
