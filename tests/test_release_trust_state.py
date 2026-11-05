from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import os
import threading
"""Tests for transactional Versionary trust-state storage."""

import base64
from contextlib import closing
import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


updates = load("release-policy-updates.py", "versionary_state_test_updates")
state = load("release-trust-state.py", "versionary_state_test_storage")


class TrustStateTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.authority = Ed25519PrivateKey.generate()
        self.authority_path = self.root / "authority.pem"
        self.authority_path.write_bytes(
            self.authority.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        self.database = self.root / "trust.db"
        self.policy = self.root / "policy.json"
        self.signature = self.root / "policy.sig.json"

        release_key = Ed25519PrivateKey.generate().public_key()
        release_raw = release_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        release_pem = release_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        self.policy.write_text(json.dumps({
            "schema_version": 1,
            "product": "Versionary",
            "keys": [{
                "key_id": "sha256:" + hashlib.sha256(release_raw).hexdigest(),
                "public_key": release_pem,
                "status": "trusted",
            }],
        }))

        state.initialize(self.database, self.authority_path)
        self.sign(1)

    def sign(self, version):
        digest = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        signature = self.authority.sign(
            updates.signed_message(version, digest)
        )
        self.signature.write_text(json.dumps({
            "schema_version": 1,
            "algorithm": "Ed25519",
            "authority_key_id": updates.key_identity(
                self.authority.public_key()
            ),
            "policy_version": version,
            "policy_sha256": digest,
            "signature": base64.b64encode(signature).decode(),
        }))

    def test_explicit_bootstrap(self):
        result = state.read_state(self.database)
        self.assertEqual(result["policy_version"], 0)

    def test_initial_install(self):
        self.assertEqual(
            state.install_update(
                self.database, self.policy, self.signature
            ),
            1,
        )
        self.assertEqual(
            state.read_state(self.database)["policy_version"], 1
        )

    def test_replay_rejected(self):
        state.install_update(self.database, self.policy, self.signature)
        with self.assertRaisesRegex(
            state._UPDATES.PolicyUpdateError,
            "rollback or replay rejected"
        ):
            state.install_update(
                self.database, self.policy, self.signature
            )

    def test_rollback_rejected(self):
        state.install_update(self.database, self.policy, self.signature)
        self.sign(2)
        state.install_update(self.database, self.policy, self.signature)
        self.sign(1)

        with self.assertRaisesRegex(
            state._UPDATES.PolicyUpdateError,
            "rollback or replay rejected"
        ):
            state.install_update(
                self.database, self.policy, self.signature
            )

    def test_invalid_signature_preserves_state(self):
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = base64.b64encode(b"\0" * 64).decode()
        self.signature.write_text(json.dumps(envelope))

        with self.assertRaisesRegex(
            state._UPDATES.PolicyUpdateError,
            "signature verification failed"
        ):
            state.install_update(
                self.database, self.policy, self.signature
            )

        self.assertEqual(
            state.read_state(self.database)["policy_version"], 0
        )

    def test_corrupted_stored_policy_rejected(self):
        state.install_update(self.database, self.policy, self.signature)

        from contextlib import closing

        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "UPDATE trust_state SET policy_bytes = ?",
                (b"tampered",),
            )

        with self.assertRaises(state.TrustStateError):
            state.read_state(self.database)

    def test_missing_database_rejected(self):
        with self.assertRaises(state.TrustStateError):
            state.read_state(self.root / "missing.db")

    def test_symlink_database_rejected(self):
        link = self.root / "linked.db"
        link.symlink_to(self.database)

        with self.assertRaises(state.TrustStateError):
            state.read_state(link)

    def test_rebootstrap_rejected(self):
        with self.assertRaises(state.TrustStateError):
            state.initialize(self.database, self.authority_path)

    def test_two_sequential_updates(self):
        state.install_update(self.database, self.policy, self.signature)
        self.sign(2)

        self.assertEqual(
            state.install_update(
                self.database, self.policy, self.signature
            ),
            2,
        )

        self.assertEqual(
            state.read_state(self.database)["policy_version"], 2
        )


    def test_stored_authority_fingerprint_tampering(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "UPDATE trust_state SET authority_key_id = ?",
                ("sha256:" + "0" * 64,),
            )
        with self.assertRaisesRegex(
            state.TrustStateError, "fingerprint mismatch"
        ):
            state.read_state(self.database)

    def test_stored_authority_key_tampering(self):
        other = Ed25519PrivateKey.generate().public_key()
        other_pem = other.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "UPDATE trust_state SET authority_public = ?",
                (other_pem,),
            )
        with self.assertRaisesRegex(
            state.TrustStateError, "fingerprint mismatch"
        ):
            state.read_state(self.database)

    def test_policy_bytes_match_authenticated_snapshot(self):
        original = self.policy.read_bytes()
        state.install_update(self.database, self.policy, self.signature)
        stored = state.read_state(self.database)
        self.assertEqual(stored["policy_bytes"], original)
        self.assertEqual(
            stored["policy_sha256"],
            hashlib.sha256(original).hexdigest(),
        )

    def test_database_permissions_rejected(self):
        self.database.chmod(0o644)
        with self.assertRaisesRegex(
            state.TrustStateError, "permissions"
        ):
            state.read_state(self.database)

    def test_extra_state_row_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("""
                INSERT INTO trust_state
                SELECT 2, authority_key_id, authority_public,
                       policy_version, policy_sha256, policy_bytes
                FROM trust_state WHERE singleton = 1
            """)
        with self.assertRaisesRegex(
            state.TrustStateError,
            "integrity check failed|inconsistent"

        ):
            state.read_state(self.database)

    def test_failed_install_does_not_advance_version(self):
        state.install_update(self.database, self.policy, self.signature)
        self.sign(2)
        envelope = json.loads(self.signature.read_text())
        envelope["signature"] = base64.b64encode(b"X" * 64).decode()
        self.signature.write_text(json.dumps(envelope))
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.install_update(
                self.database, self.policy, self.signature
            )
        self.assertEqual(
            state.read_state(self.database)["policy_version"], 1
        )

    def test_missing_state_row_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("DELETE FROM trust_state")
        with self.assertRaisesRegex(
            state.TrustStateError, "inconsistent"
        ):
            state.read_state(self.database)

    def test_immutable_bytes_api_rejects_modified_policy(self):
        policy = self.policy.read_bytes()
        signature = self.signature.read_bytes()
        authority = self.authority_path.read_bytes()
        self.assertEqual(
            updates.verify_update_bytes(
                policy, signature, authority, 0
            ), 1
        )
        with self.assertRaisesRegex(
            updates.PolicyUpdateError, "digest mismatch"
        ):
            updates.verify_update_bytes(
                policy + b"\\n", signature, authority, 0
            )


    def test_concurrent_installations_serialized(self):
        """Two installers cannot both advance the same version."""
        barrier = threading.Barrier(2)

        def worker(_):
            barrier.wait(timeout=10)
            try:
                return ("ok", state.install_update(
                    self.database, self.policy, self.signature
                ))
            except state._UPDATES.PolicyUpdateError:
                return ("rejected", None)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))

        self.assertEqual(
            sorted(result[0] for result in results),
            ["ok", "rejected"],
        )
        self.assertEqual(
            state.read_state(self.database)["policy_version"], 1
        )

    def test_database_transaction_rolls_back_on_write_failure(self):
        """An aborted SQLite write must not alter trusted state."""
        original = state.read_state(self.database)

        with self.assertRaises(RuntimeError):
            with closing(state.connect(self.database)) as connection:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "UPDATE trust_state SET policy_version = 999 "
                        "WHERE singleton = 1"
                    )
                    raise RuntimeError("Simulated interruption")

        self.assertEqual(state.read_state(self.database), original)

    def test_policy_replacement_after_capture_does_not_change_stored_bytes(self):
        """Storage must use the captured, authenticated snapshot."""
        original = self.policy.read_bytes()
        real_read = state._UPDATES.read_regular
        changed = False

        def capture_then_replace(path, *args, **kwargs):
            nonlocal changed
            result = real_read(path, *args, **kwargs)
            if Path(path) == self.policy and not changed:
                changed = True
                self.policy.write_bytes(b'{"tampered":true}')
            return result

        with patch.object(
            state._UPDATES, "read_regular",
            side_effect=capture_then_replace,
        ):
            self.assertEqual(
                state.install_update(
                    self.database, self.policy, self.signature
                ), 1
            )

        self.assertEqual(
            state.read_state(self.database)["policy_bytes"], original
        )

    def test_authority_file_changes_do_not_change_pinned_identity(self):
        """Trust authority remains pinned to explicit bootstrap."""
        original = state.read_state(self.database)["authority_key_id"]
        self.authority_path.write_bytes(b"not an authority key")
        self.assertEqual(
            state.read_state(self.database)["authority_key_id"], original
        )
        self.assertEqual(
            state.install_update(
                self.database, self.policy, self.signature
            ), 1
        )

    def test_invalid_stored_version_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection:
            with connection:
                connection.execute(
                    "PRAGMA ignore_check_constraints=ON"
                )
                connection.execute(
                    "UPDATE trust_state SET policy_version = -1"
                )
        with self.assertRaises(state.TrustStateError):
            state.read_state(self.database)

    def test_stored_policy_without_digest_rejected(self):
        state.install_update(
            self.database, self.policy, self.signature
        )
        with closing(sqlite3.connect(self.database)) as connection:
            with connection:
                connection.execute(
                    "UPDATE trust_state SET policy_sha256 = NULL"
                )
        with self.assertRaises(state.TrustStateError):
            state.read_state(self.database)

    def test_world_writable_database_rejected(self):
        self.database.chmod(0o666)
        with self.assertRaises(state.TrustStateError):
            state.read_state(self.database)

    def test_bootstrap_requires_existing_directory(self):
        missing = self.root / "nonexistent" / "trust.db"
        with self.assertRaises(state.TrustStateError):
            state.initialize(missing, self.authority_path)
        self.assertFalse(missing.exists())


    def test_phase4_symlinked_policy_rejected(self):
        target = self.root / "policy-alias.json"
        target.symlink_to(self.policy)
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.install_update(
                self.database, target, self.signature
            )

    def test_phase4_symlinked_signature_rejected(self):
        target = self.root / "signature-alias.json"
        target.symlink_to(self.signature)
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.install_update(
                self.database, self.policy, target
            )

    def test_phase4_symlinked_authority_rejected(self):
        alias = self.root / "authority-alias.pem"
        alias.symlink_to(self.authority_path)
        second = self.root / "second.db"
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.initialize(second, alias)
        self.assertFalse(second.exists())

    def test_phase4_public_database_directory_rejected(self):
        public = self.root / "public"
        public.mkdir(mode=0o755)
        database = public / "trust.db"
        with self.assertRaisesRegex(
            state.TrustStateError, "private"
        ):
            state.initialize(database, self.authority_path)
        self.assertFalse(database.exists())

    def test_phase4_private_database_directory_accepted(self):
        private = self.root / "private"
        private.mkdir(mode=0o700)
        database = private / "trust.db"
        identity = state.initialize(
            database, self.authority_path
        )
        self.assertEqual(
            state.read_state(database)["authority_key_id"],
            identity,
        )

    def test_phase4_nonregular_policy_rejected(self):
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.install_update(
                self.database, self.root, self.signature
            )

    def test_phase4_oversized_policy_rejected(self):
        huge = self.root / "huge-policy.json"
        huge.write_bytes(
            b"X" * (state._UPDATES.MAX_BYTES + 1)
        )
        with self.assertRaises(state._UPDATES.PolicyUpdateError):
            state.install_update(
                self.database, huge, self.signature
            )
        self.assertEqual(
            state.read_state(self.database)["policy_version"], 0
        )


if __name__ == "__main__":
    unittest.main()
