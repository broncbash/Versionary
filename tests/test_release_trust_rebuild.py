"""Missing-database recovery safety tests."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_release_trust_recovery import RecoveryTests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "versionary_rebuild_tests",
    ROOT / "installer/release-trust-rebuild.py",
)
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


class RebuildTests(unittest.TestCase):
    """Reuse fixture setup and signing without inheriting tests."""

    setUp = RecoveryTests.setUp
    sign = RecoveryTests.sign

    def target(self):
        return self.root / "rebuilt.db"

    def run_rebuild(self, floor=1, target=None):
        return rebuild.rebuild(
            target or self.target(),
            self.authority_path,
            self.policy_path,
            self.signature_path,
            floor,
        )

    def test_rebuild_reads_each_input_once(self):
        original = rebuild.updates.read_regular
        counts = {}

        def counted(path, limit=rebuild.updates.MAX_BYTES):
            key = str(path)
            counts[key] = counts.get(key, 0) + 1
            return original(path, limit)

        with patch.object(
            rebuild.updates, "read_regular", side_effect=counted
        ):
            self.run_rebuild()

        self.assertEqual(counts[str(self.authority_path)], 1)
        self.assertEqual(counts[str(self.policy_path)], 1)
        self.assertEqual(counts[str(self.signature_path)], 1)

    def test_rebuild_does_not_leave_staging_files(self):
        self.run_rebuild()
        self.assertEqual(
            list(self.root.glob(".versionary-rebuild-*")), []
        )

    def test_rebuild_rejects_dangling_destination_symlink(self):
        target = self.target()
        target.symlink_to(self.root / "missing.db")
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild()
        self.assertTrue(target.is_symlink())

    def test_rebuild_result_is_private(self):
        self.run_rebuild()
        self.assertEqual(
            self.target().stat().st_mode & 0o777, 0o600
        )

    def test_staging_database_failure_preserves_destination(self):
        original_connect = rebuild.sqlite3.connect

        def fail_staging(path, *args, **kwargs):
            if ".versionary-rebuild-" in str(path):
                raise rebuild.sqlite3.OperationalError(
                    "Injected staging failure"
                )
            return original_connect(path, *args, **kwargs)

        with patch.object(
            rebuild.sqlite3, "connect", side_effect=fail_staging
        ):
            with self.assertRaises(
                rebuild.sqlite3.OperationalError
            ):
                self.run_rebuild()

        self.assertFalse(self.target().exists())
        self.assertEqual(
            list(self.root.glob(".versionary-rebuild-*")), []
        )

    def test_destination_collision_during_publication(self):
        original_link = rebuild.os.link
        sentinel = b"existing destination"

        def collide(src, dst, *args, **kwargs):
            self.target().write_bytes(sentinel)
            return original_link(src, dst, *args, **kwargs)

        with patch.object(
            rebuild.os, "link", side_effect=collide
        ):
            with self.assertRaises(rebuild.RebuildError):
                self.run_rebuild()

        self.assertEqual(self.target().read_bytes(), sentinel)
        self.assertEqual(
            list(self.root.glob(".versionary-rebuild-*")), []
        )

    def test_fsync_failure_before_publication(self):
        original_fsync = rebuild.os.fsync
        calls = {"count": 0}

        def fail_first(fd):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("Injected fsync failure")
            return original_fsync(fd)

        with patch.object(
            rebuild.os, "fsync", side_effect=fail_first
        ):
            with self.assertRaises(OSError):
                self.run_rebuild()

        self.assertFalse(self.target().exists())
        self.assertEqual(
            list(self.root.glob(".versionary-rebuild-*")), []
        )

    def test_fsync_failure_after_publication(self):
        original_fsync = rebuild.os.fsync
        calls = {"count": 0}

        def fail_second(fd):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("Injected directory fsync failure")
            return original_fsync(fd)

        with patch.object(
            rebuild.os, "fsync", side_effect=fail_second
        ):
            with self.assertRaises(OSError):
                self.run_rebuild()

        # Publication has already occurred. Never overwrite it.
        self.assertTrue(self.target().exists())
        self.assertEqual(
            rebuild.state.read_state(
                self.target()
            )["policy_version"], 1
        )
        self.assertEqual(
            list(self.root.glob(".versionary-rebuild-*")), []
        )

    def test_rebuild_success(self):
        result = self.run_rebuild()
        self.assertEqual(result["status"], "rebuilt")
        self.assertEqual(
            rebuild.state.read_state(self.target())["policy_version"],
            1,
        )

    def test_rebuild_never_overwrites(self):
        self.run_rebuild()
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild()

    def test_rebuild_rejects_missing_floor(self):
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild(0)
        self.assertFalse(self.target().exists())

    def test_rebuild_rejects_high_floor(self):
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild(2)
        self.assertFalse(self.target().exists())

    def test_rebuild_rejects_symlink(self):
        alias = self.root / "alias-rebuild.db"
        alias.symlink_to(self.database)
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild(target=alias)

    def test_rebuild_rejects_invalid_signature_before_creation(self):
        self.signature_path.write_bytes(b"{}")
        with self.assertRaises(
            rebuild.updates.PolicyUpdateError
        ):
            self.run_rebuild()
        self.assertFalse(self.target().exists())

    def test_rebuild_rejects_relative_target(self):
        with self.assertRaises(rebuild.RebuildError):
            self.run_rebuild(target=Path("relative.db"))

    def test_rebuild_rejects_tampered_policy(self):
        self.policy_path.write_bytes(
            self.policy_path.read_bytes() + b" "
        )
        with self.assertRaises(
            rebuild.updates.PolicyUpdateError
        ):
            self.run_rebuild()
        self.assertFalse(self.target().exists())
