#!/usr/bin/env python3
"""Versionary offline Ed25519 release trust-policy validation."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_POLICY_BYTES = 1024 * 1024
MAX_KEYS = 32
KEY_ID_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class TrustPolicyError(Exception):
    pass


def public_key_id(key):
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def load_policy(path):
    path = Path(path)

    if path.is_symlink() or not path.is_file():
        raise TrustPolicyError("Trust policy must be a regular file")

    if path.stat().st_size > MAX_POLICY_BYTES:
        raise TrustPolicyError("Trust policy exceeds size limit")

    with path.open("rb") as stream:
        raw = stream.read(MAX_POLICY_BYTES + 1)

    if len(raw) > MAX_POLICY_BYTES:
        raise TrustPolicyError("Trust policy exceeds size limit")

    def reject_duplicates(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise TrustPolicyError(f"Duplicate JSON field: {name}")
            result[name] = value
        return result

    try:
        policy = json.loads(raw, object_pairs_hook=reject_duplicates)
    except (ValueError, UnicodeError) as exc:
        raise TrustPolicyError("Invalid trust-policy JSON") from exc

    return validate_policy(policy)


def validate_policy(policy):
    if not isinstance(policy, dict):
        raise TrustPolicyError("Trust policy must be an object")

    if set(policy) != {"schema_version", "product", "keys"}:
        raise TrustPolicyError("Unexpected trust-policy fields")

    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise TrustPolicyError("Unsupported trust-policy schema")

    if policy["product"] != "Versionary":
        raise TrustPolicyError("Incorrect product identity")

    entries = policy["keys"]

    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_KEYS:
        raise TrustPolicyError("Invalid trust-policy key count")

    seen = set()
    validated = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise TrustPolicyError("Key entry must be an object")

        if set(entry) != {"key_id", "public_key", "status"}:
            raise TrustPolicyError("Unexpected key-entry fields")

        identity = entry["key_id"]
        pem = entry["public_key"]
        status = entry["status"]

        if not isinstance(identity, str) or not KEY_ID_RE.fullmatch(identity):
            raise TrustPolicyError("Invalid key identifier")

        if not isinstance(pem, str) or len(pem) > 8192:
            raise TrustPolicyError("Invalid public-key encoding")

        if status not in ("trusted", "revoked"):
            raise TrustPolicyError("Invalid key status")

        try:
            key = serialization.load_pem_public_key(pem.encode("ascii"))
        except (ValueError, TypeError, UnicodeError) as exc:
            raise TrustPolicyError("Invalid public key") from exc

        if not isinstance(key, Ed25519PublicKey):
            raise TrustPolicyError("Trust policy requires Ed25519 keys")

        if public_key_id(key) != identity:
            raise TrustPolicyError("Public-key fingerprint mismatch")

        if identity in seen:
            raise TrustPolicyError("Duplicate signing key")

        seen.add(identity)
        validated[identity] = (status, key)

    return validated


def trusted_key(policy_path, identity):
    keys = load_policy(policy_path)

    if identity not in keys:
        raise TrustPolicyError("Unknown release signing key")

    status, key = keys[identity]

    if status != "trusted":
        raise TrustPolicyError("Release signing key is revoked")

    return key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args(argv)

    try:
        key = trusted_key(args.policy, args.key_id)
        print("[PASS] Release signing key is trusted")
        print("Key ID:", public_key_id(key))
        return 0
    except (TrustPolicyError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
