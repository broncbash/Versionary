#!/usr/bin/env python3
"""Offline authenticated Versionary trust-policy update validation."""

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import stat
import re
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024
MAX_VERSION = 2**63 - 1
KEY_ID_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


class PolicyUpdateError(Exception):
    pass


def read_regular(path, limit=MAX_BYTES):
    """Read one bounded regular file without following its final symlink."""
    path = Path(path)

    if not hasattr(os, "O_NOFOLLOW"):
        raise PolicyUpdateError("O_NOFOLLOW is required")

    flags = os.O_RDONLY | os.O_NOFOLLOW
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)

    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PolicyUpdateError("Cannot securely open input file") from exc

    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise PolicyUpdateError("Expected a regular file")
        if before.st_size > limit:
            raise PolicyUpdateError("File exceeds size limit")

        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)

        after = os.fstat(descriptor)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise PolicyUpdateError("Input changed while being read")

        if len(data) > limit:
            raise PolicyUpdateError("File exceeds size limit")

        return data
    finally:
        os.close(descriptor)


def parse_json(raw):
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PolicyUpdateError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=no_duplicates)
    except (ValueError, UnicodeError) as exc:
        raise PolicyUpdateError("Invalid JSON") from exc


def key_identity(key):
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def validate_version(version):
    if type(version) is not int or not 1 <= version <= MAX_VERSION:
        raise PolicyUpdateError("Invalid policy version")
    return version


def load_authority(path):
    raw = read_regular(path, 8192)
    try:
        key = serialization.load_pem_public_key(raw)
    except (ValueError, TypeError) as exc:
        raise PolicyUpdateError("Invalid authority public key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise PolicyUpdateError("Policy authority must use Ed25519")
    return key


def validate_envelope(raw):
    envelope = parse_json(raw)
    if not isinstance(envelope, dict) or set(envelope) != {
        "schema_version",
        "algorithm",
        "authority_key_id",
        "policy_version",
        "policy_sha256",
        "signature",
    }:
        raise PolicyUpdateError("Invalid policy signature envelope")

    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise PolicyUpdateError("Unsupported envelope schema")

    if envelope["algorithm"] != "Ed25519":
        raise PolicyUpdateError("Unsupported signature algorithm")

    if not isinstance(envelope["authority_key_id"], str) or not KEY_ID_RE.fullmatch(
        envelope["authority_key_id"]
    ):
        raise PolicyUpdateError("Invalid authority identity")

    validate_version(envelope["policy_version"])

    if not isinstance(envelope["policy_sha256"], str) or not SHA_RE.fullmatch(
        envelope["policy_sha256"]
    ):
        raise PolicyUpdateError("Invalid policy digest")

    try:
        signature = base64.b64decode(
            envelope["signature"], validate=True
        )
    except (ValueError, TypeError) as exc:
        raise PolicyUpdateError("Invalid signature encoding") from exc

    if len(signature) != 64:
        raise PolicyUpdateError("Invalid Ed25519 signature length")

    return envelope, signature


def signed_message(version, digest):
    return (
        b"VERSIONARY-POLICY-UPDATE-V1\n"
        + str(validate_version(version)).encode("ascii")
        + b"\n"
        + digest.encode("ascii")
        + b"\n"
    )


def verify_update_bytes(
    policy_bytes,
    signature_bytes,
    authority_bytes,
    current_version,
):
    """Authenticate immutable input bytes; never reread their source."""
    if (
        type(current_version) is not int
        or not 0 <= current_version <= MAX_VERSION
    ):
        raise PolicyUpdateError("Invalid current policy version")

    if not isinstance(policy_bytes, bytes) or len(policy_bytes) > MAX_BYTES:
        raise PolicyUpdateError("Invalid policy bytes")
    if not isinstance(signature_bytes, bytes) or len(signature_bytes) > 16384:
        raise PolicyUpdateError("Invalid signature bytes")
    if not isinstance(authority_bytes, bytes) or len(authority_bytes) > 8192:
        raise PolicyUpdateError("Invalid authority bytes")

    try:
        authority = serialization.load_pem_public_key(authority_bytes)
    except (ValueError, TypeError) as exc:
        raise PolicyUpdateError("Invalid authority public key") from exc

    if not isinstance(authority, Ed25519PublicKey):
        raise PolicyUpdateError("Policy authority must use Ed25519")

    envelope, signature = validate_envelope(signature_bytes)

    if envelope["authority_key_id"] != key_identity(authority):
        raise PolicyUpdateError("Untrusted policy authority")

    digest = hashlib.sha256(policy_bytes).hexdigest()
    if envelope["policy_sha256"] != digest:
        raise PolicyUpdateError("Policy digest mismatch")

    version = envelope["policy_version"]
    if version <= current_version:
        raise PolicyUpdateError("Policy rollback or replay rejected")

    try:
        authority.verify(signature, signed_message(version, digest))
    except InvalidSignature as exc:
        raise PolicyUpdateError(
            "Policy signature verification failed"
        ) from exc

    spec = importlib.util.spec_from_file_location(
        "versionary_policy_validator",
        ROOT / "installer/release-trust-policy.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_policy(parse_json(policy_bytes))
    return version


def verify_update(
    policy_path,
    signature_path,
    authority_path,
    current_version,
):
    """Read inputs once and authenticate the captured bytes."""
    return verify_update_bytes(
        read_regular(policy_path),
        read_regular(signature_path, 16384),
        read_regular(authority_path, 8192),
        current_version,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--signature", required=True, type=Path)
    parser.add_argument("--authority-public", required=True, type=Path)
    parser.add_argument("--current-version", required=True, type=int)
    args = parser.parse_args(argv)

    try:
        version = verify_update(
            args.policy,
            args.signature,
            args.authority_public,
            args.current_version,
        )
        print("[PASS] Authenticated policy update verified")
        print("[INFO] New policy version:", version)
        print("[INFO] No trust state was modified")
        return 0
    except (PolicyUpdateError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
