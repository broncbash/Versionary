#!/usr/bin/env python3
"""Offline Ed25519 signing for Versionary release manifests.

This tool authenticates a manifest's bytes using an explicitly trusted
public key. It does not authorize production deployment and does not
replace package/provenance verification.
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

SCHEMA = 1
ALGORITHM = "Ed25519"
MAX_MANIFEST = 1024 * 1024
MAX_SIGNATURE = 16 * 1024
MAX_KEY = 16 * 1024
KEY_ID_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class SigningError(Exception):
    pass


def read_regular(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SigningError(f"Not a regular file: {path}")
    if path.stat().st_size > limit:
        raise SigningError(f"File exceeds size limit: {path}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise SigningError(f"File exceeds size limit: {path}")
    return data


def write_new(path, data, mode):
    path = Path(path)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def public_bytes(key):
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def key_id(key):
    return "sha256:" + hashlib.sha256(public_bytes(key)).hexdigest()


def load_private(path):
    data = read_regular(path, MAX_KEY)
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SigningError("Signing key must be Ed25519")
    return key


def load_public(path):
    data = read_regular(path, MAX_KEY)
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise SigningError("Trusted key must be Ed25519")
    return key


def keygen(private_path, public_path):
    private_path = Path(private_path)
    public_path = Path(public_path)

    if private_path == public_path:
        raise SigningError("Private and public paths must differ")

    if private_path.exists() or private_path.is_symlink():
        raise SigningError("Private key destination already exists")

    if public_path.exists() or public_path.is_symlink():
        raise SigningError("Public key destination already exists")

    key = Ed25519PrivateKey.generate()
    private_data = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_data = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    write_new(private_path, private_data, 0o600)
    try:
        write_new(public_path, public_data, 0o644)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise

    return key_id(key.public_key())


def sign(manifest_path, private_path, output_path):
    manifest = read_regular(manifest_path, MAX_MANIFEST)
    key = load_private(private_path)
    signature = key.sign(manifest)

    envelope = {
        "schema_version": SCHEMA,
        "algorithm": ALGORITHM,
        "key_id": key_id(key.public_key()),
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "signature": base64.b64encode(signature).decode("ascii"),
    }

    data = (
        json.dumps(envelope, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    write_new(output_path, data, 0o644)
    return envelope["key_id"]


def verify(manifest_path, signature_path, trusted_public_path):
    manifest = read_regular(manifest_path, MAX_MANIFEST)
    raw = read_regular(signature_path, MAX_SIGNATURE)
    key = load_public(trusted_public_path)

    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise SigningError("Invalid signature envelope") from exc

    if not isinstance(envelope, dict):
        raise SigningError("Signature envelope must be an object")

    required = {
        "schema_version",
        "algorithm",
        "key_id",
        "manifest_sha256",
        "signature",
    }
    if set(envelope) != required:
        raise SigningError("Unexpected signature envelope fields")

    if (
        type(envelope["schema_version"]) is not int
        or envelope["schema_version"] != SCHEMA
        or envelope["algorithm"] != ALGORITHM
    ):
        raise SigningError("Unsupported signature format")

    claimed_id = envelope["key_id"]
    if not isinstance(claimed_id, str) or not KEY_ID_RE.fullmatch(claimed_id):
        raise SigningError("Invalid key identifier")

    if claimed_id != key_id(key):
        raise SigningError("Signing key is not the trusted key")

    digest = hashlib.sha256(manifest).hexdigest()
    if envelope["manifest_sha256"] != digest:
        raise SigningError("Manifest checksum mismatch")

    encoded = envelope["signature"]
    if not isinstance(encoded, str):
        raise SigningError("Signature must be base64 text")

    try:
        signature = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SigningError("Invalid signature encoding") from exc

    if len(signature) != 64:
        raise SigningError("Invalid Ed25519 signature length")

    try:
        key.verify(signature, manifest)
    except InvalidSignature as exc:
        raise SigningError("Ed25519 signature verification failed") from exc

    return claimed_id


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("keygen")
    generate.add_argument("--private", required=True, type=Path)
    generate.add_argument("--public", required=True, type=Path)

    signer = commands.add_parser("sign")
    signer.add_argument("--manifest", required=True, type=Path)
    signer.add_argument("--private", required=True, type=Path)
    signer.add_argument("--output", required=True, type=Path)

    verifier = commands.add_parser("verify")
    verifier.add_argument("--manifest", required=True, type=Path)
    verifier.add_argument("--signature", required=True, type=Path)
    verifier.add_argument("--trusted-public", required=True, type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "keygen":
            identity = keygen(args.private, args.public)
            print("[OK] Ed25519 signing keypair created")
            print(f"Public key identity: {identity}")

        elif args.command == "sign":
            identity = sign(args.manifest, args.private, args.output)
            print("[OK] Detached release signature created")
            print(f"Signing key identity: {identity}")

        elif args.command == "verify":
            identity = verify(
                args.manifest,
                args.signature,
                args.trusted_public,
            )
            print("[PASS] Trusted release signature verified")
            print(f"Trusted key identity: {identity}")

        return 0

    except (
        SigningError,
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
