"""Read-only coordinated rollback planning regression tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "installer"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, BASE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planner = load("rollback_planner_tests", "rollback-plan.py")
snapshots = load("rollback_snapshot_tests", "installation-snapshot.py")


class RollbackPlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.root = base / "root"
        self.root.mkdir(mode=0o700)
        self.config = self.root / "etc/versionary-agent/config.json"
        self.config.parent.mkdir(parents=True)
        self.config.write_text('{"value":"old"}')
        self.config.chmod(0o600)
        self.snapshot = base / "snapshot"
        snapshots.snapshot(self.root, self.snapshot)

    def test_unchanged_assets(self):
        result = planner.plan(self.root, self.snapshot)
        self.assertEqual(result["change_count"], 0)
        self.assertFalse(result["apply_allowed"])
        self.assertFalse(result["changes_made"])
        self.assertEqual(len(result["changes"]), 4)

    def test_changed_config(self):
        self.config.write_text('{"value":"new"}')
        result = planner.plan(self.root, self.snapshot)
        self.assertEqual(result["changes"][0]["action"], "replace")
        self.assertEqual(result["change_count"], 1)
        self.assertEqual(self.config.read_text(), '{"value":"new"}')

    def test_missing_current_asset(self):
        self.config.unlink()
        result = planner.plan(self.root, self.snapshot)
        self.assertEqual(result["changes"][0]["action"], "create")

    def test_proposed_removal_blocker(self):
        extra = self.root / "etc/versionary-agent/ca.crt"
        extra.write_text("CA")
        extra.chmod(0o600)
        result = planner.plan(self.root, self.snapshot)
        self.assertEqual(result["changes"][1]["action"], "remove")
        self.assertTrue(any("removal" in b for b in result["blockers"]))

    def test_live_root_refused(self):
        with self.assertRaises(ValueError):
            planner.plan("/", self.snapshot)

    def test_overlap_refused(self):
        with self.assertRaises(ValueError):
            planner.plan(self.root, self.root)

    def test_tampered_snapshot_refused(self):
        (self.snapshot / "asset-0").write_text("tampered")
        with self.assertRaises(ValueError):
            planner.plan(self.root, self.snapshot)

    def test_symlink_source_refused(self):
        self.config.unlink()
        self.config.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):
            planner.plan(self.root, self.snapshot)

    def test_private_state_excluded(self):
        state = self.root / "var/lib/versionary-agent"
        state.mkdir(parents=True, mode=0o700)
        state.chmod(0o700)
        (state / "token").write_text("secret-do-not-read")
        result = planner.plan(self.root, self.snapshot)
        self.assertTrue(any("Private state" in b for b in result["blockers"]))
        self.assertNotIn("secret-do-not-read", json.dumps(result))
        self.assertFalse(result["credential_contents_read"])


if __name__ == "__main__":
    unittest.main()
