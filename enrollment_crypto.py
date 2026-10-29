"""Ed25519 primitives for ARBY PATCH COMMAND enrollment."""

import base64
import binascii
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class EnrollmentCryptoError(ValueError):
    """Invalid enrollment cryptographic material."""


def encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_bytes(value: str, expected_length: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise EnrollmentCryptoError("Invalid encoded value")

    if len(value) > 256:
        raise EnrollmentCryptoError("Encoded value too long")

    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, binascii.Error) as exc:
        raise EnrollmentCryptoError("Invalid base64 encoding") from exc

    if len(decoded) != expected_length or encode_bytes(decoded) != value:
        raise EnrollmentCryptoError("Invalid encoded value length or format")

    return decoded


def generate_keypair():
    """Generate an Ed25519 private key and encoded public key."""
    private_key = Ed25519PrivateKey.generate()

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return private_key, encode_bytes(public_bytes)


def generate_challenge() -> str:
    """Generate a 256-bit unpredictable enrollment challenge."""
    return encode_bytes(secrets.token_bytes(32))


def sign_challenge(private_key, challenge: str) -> str:
    """Sign a domain-separated enrollment challenge."""
    challenge_bytes = decode_bytes(challenge, 32)

    message = b"ARBY-PATCH-ENROLLMENT-V1:" + challenge_bytes
    return encode_bytes(private_key.sign(message))


def verify_challenge(
    public_key: str,
    challenge: str,
    signature: str,
) -> bool:
    """Verify an Ed25519 enrollment challenge signature."""
    try:
        key_bytes = decode_bytes(public_key, 32)
        challenge_bytes = decode_bytes(challenge, 32)
        signature_bytes = decode_bytes(signature, 64)

        key = Ed25519PublicKey.from_public_bytes(key_bytes)
        key.verify(
            signature_bytes,
            b"ARBY-PATCH-ENROLLMENT-V1:" + challenge_bytes,
        )
        return True
    except (EnrollmentCryptoError, InvalidSignature, ValueError):
        return False
