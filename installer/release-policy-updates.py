#!/usr/bin/env python3
"""Offline authenticated Versionary trust-policy update validation."""

import argparse
import base64
import hashlib
import importlib.util
import json
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
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise PolicyUpdateError("Expected a regular file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PolicyUpdateError("File exceeds size limit")
    return data


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


def verify_update(
    policy_path,
    signature_path,
    authority_path,
    current_version,
):
    current_version = validate_version(current_version)

    policy_bytes = read_regular(policy_path)
    signature_bytes = read_regular(signature_path, 16384)
    authority = load_authority(authority_path)

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
        raise PolicyUpdateError("Policy signature verification failed") from exc

    spec = importlib.util.spec_from_file_location(
        "versionary_policy_validator",
        ROOT / "installer/release-trust-policy.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.validate_policy(parse_json(policy_bytes))

    return version


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
