"""Agent-side cryptography for Versionary enrollment v2."""

import base64
import hashlib
import re

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


DOMAIN = b"ARBY-PATCH-ENROLLMENT-V2:"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class EnrollmentCryptoError(ValueError):
    """Invalid enrollment cryptographic material."""


def encode_bytes(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def decode_bytes(value, expected_length):
    if not isinstance(value, str):
        raise EnrollmentCryptoError("Invalid encoded value")

    try:
        raw = base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, base64.binascii.Error) as exc:
        raise EnrollmentCryptoError("Invalid base64 encoding") from exc

    if len(raw) != expected_length or encode_bytes(raw) != value:
        raise EnrollmentCryptoError("Invalid encoded length or format")

    return raw


def generate_keypair():
    private_key = Ed25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return encode_bytes(private_bytes), encode_bytes(public_bytes)


def public_key_from_private(private_key):
    key = Ed25519PrivateKey.from_private_bytes(
        decode_bytes(private_key, 32)
    )

    return encode_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def enrollment_message(agent_id, challenge, credential_hash):
    if not isinstance(agent_id, str) or not agent_id:
        raise EnrollmentCryptoError("Invalid agent identity")

    if (
        not isinstance(credential_hash, str)
        or not HASH_PATTERN.fullmatch(credential_hash)
    ):
        raise EnrollmentCryptoError("Invalid credential hash")

    challenge_bytes = decode_bytes(challenge, 32)

    return (
        DOMAIN
        + agent_id.encode("utf-8")
        + b":"
        + challenge_bytes
        + b":"
        + bytes.fromhex(credential_hash)
    )


def sign_enrollment(
    private_key,
    agent_id,
    challenge,
    credential_hash,
):
    key = Ed25519PrivateKey.from_private_bytes(
        decode_bytes(private_key, 32)
    )

    signature = key.sign(
        enrollment_message(
            agent_id,
            challenge,
            credential_hash,
        )
    )

    return encode_bytes(signature)


def hash_credential(token):
    if not isinstance(token, str) or not token:
        raise EnrollmentCryptoError("Invalid credential")

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
