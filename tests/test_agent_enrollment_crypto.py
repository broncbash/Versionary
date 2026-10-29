"""Tests for the standalone agent enrollment cryptography."""

import hashlib
import secrets
import unittest
from uuid import uuid4

from agent.enrollment_crypto import (
    generate_keypair,
    public_key_from_private,
    sign_enrollment,
    hash_credential,
    decode_bytes,
    EnrollmentCryptoError,
)
from enrollment_crypto import generate_challenge
from enrollment_recoverable import verify_enrollment_signature


class TestAgentEnrollmentCrypto(unittest.TestCase):

    def setUp(self):
        self.private_key, self.public_key = generate_keypair()
        self.agent_id = str(uuid4())
        self.challenge = generate_challenge()
        self.token = secrets.token_urlsafe(48)
        self.credential_hash = hashlib.sha256(
            self.token.encode()
        ).hexdigest()

    def test_keypair(self):
        self.assertEqual(
            public_key_from_private(self.private_key),
            self.public_key,
        )

    def test_signature_matches_server(self):
        signature = sign_enrollment(
            self.private_key,
            self.agent_id,
            self.challenge,
            self.credential_hash,
        )

        self.assertTrue(
            verify_enrollment_signature(
                self.public_key,
                self.agent_id,
                self.challenge,
                self.credential_hash,
                signature,
            )
        )

    def test_wrong_credential_hash_fails(self):
        signature = sign_enrollment(
            self.private_key,
            self.agent_id,
            self.challenge,
            self.credential_hash,
        )

        self.assertFalse(
            verify_enrollment_signature(
                self.public_key,
                self.agent_id,
                self.challenge,
                hashlib.sha256(b"other").hexdigest(),
                signature,
            )
        )

    def test_wrong_agent_identity_fails(self):
        signature = sign_enrollment(
            self.private_key,
            self.agent_id,
            self.challenge,
            self.credential_hash,
        )

        self.assertFalse(
            verify_enrollment_signature(
                self.public_key,
                str(uuid4()),
                self.challenge,
                self.credential_hash,
                signature,
            )
        )

    def test_hash_credential(self):
        self.assertEqual(
            hash_credential(self.token),
            self.credential_hash,
        )

    def test_invalid_private_key(self):
        with self.assertRaises(EnrollmentCryptoError):
            sign_enrollment(
                "invalid",
                self.agent_id,
                self.challenge,
                self.credential_hash,
            )

    def test_invalid_challenge(self):
        with self.assertRaises(EnrollmentCryptoError):
            sign_enrollment(
                self.private_key,
                self.agent_id,
                "invalid",
                self.credential_hash,
            )

    def test_invalid_credential_hash(self):
        with self.assertRaises(EnrollmentCryptoError):
            sign_enrollment(
                self.private_key,
                self.agent_id,
                self.challenge,
                "invalid",
            )


if __name__ == "__main__":
    unittest.main()
