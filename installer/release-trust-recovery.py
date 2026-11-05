#!/usr/bin/env python3
"""Development-only authenticated recovery into EXISTING trust state.

No database creation, replacement, implicit bootstrap, or production use.
The caller must supply an independently trusted authority and version floor.
"""

import hashlib
import importlib.util
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "installer" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state = load("release-trust-state.py", "versionary_recovery_state")
updates = state._UPDATES


class RecoveryError(Exception):
    pass


def recover(
    database,
    authority_public,
    policy_path,
    signature_path,
    minimum_version,
):
    """Authenticate and apply a non-rollback transition atomically.

    minimum_version is a REQUIRED externally trusted floor.
    It is not derived from the database or an unauthenticated export.
    """
    if (
        type(minimum_version) is not int
        or not 0 <= minimum_version <= updates.MAX_VERSION
    ):
        raise RecoveryError("Invalid minimum policy version")

    authority_bytes = updates.read_regular(authority_public, 8192)
    identity = state._authority_identity(authority_bytes)

    policy = updates.read_regular(policy_path)
    signature = updates.read_regular(signature_path, 16384)

    with closing(state.connect(Path(database))) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            current = state.current_state(connection)

            if identity != current["authority_key_id"]:
                raise RecoveryError("Independent authority mismatch")

            # Verify that the independently supplied public key
            # is identical to the pinned public key, regardless
            # of differences in PEM formatting.
            from cryptography.hazmat.primitives import serialization

            supplied_key = serialization.load_pem_public_key(
                authority_bytes
            )
            stored_key = serialization.load_pem_public_key(
                current["authority_public"]
            )

            supplied_raw = supplied_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            stored_raw = stored_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

            if supplied_raw != stored_raw:
                raise RecoveryError("Authority public key mismatch")

            # Validate against the pinned authority bytes, rather than
            # trusting a potentially substituted input PEM encoding.
            envelope, unused_signature = updates.validate_envelope(signature)
            version = envelope["policy_version"]

            if version < minimum_version:
                raise RecoveryError("Policy below trusted minimum version")

            if version < current["policy_version"]:
                raise RecoveryError("Policy rollback rejected")

            # Strict signature verification, even for a no-op replay.
            verified = updates.verify_update_bytes(
                policy,
                signature,
                current["authority_public"],
                version - 1,
            )

            if verified != version:
                raise RecoveryError("Unexpected verified policy version")

            digest = hashlib.sha256(policy).hexdigest()

            if version == current["policy_version"]:
                if (
                    current["policy_bytes"] != policy
                    or current["policy_sha256"] != digest
                ):
                    raise RecoveryError(
                        "Conflicting policy at existing version"
                    )
                return {
                    "status": "unchanged",
                    "policy_version": version,
                    "authority_key_id": identity,
                }

            result = connection.execute(
                """UPDATE trust_state
                   SET policy_version = ?,
                       policy_sha256 = ?,
                       policy_bytes = ?
                   WHERE singleton = 1""",
                (version, digest, policy),
            )

            if result.rowcount != 1:
                raise RecoveryError("Trust-state recovery update failed")

    return {
        "status": "recovered",
        "policy_version": version,
        "authority_key_id": identity,
    }
