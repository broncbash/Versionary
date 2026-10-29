"""Tests for enrollment cryptographic primitives."""

import unittest

from enrollment_crypto import (
    decode_bytes,
    encode_bytes,
    generate_challenge,
    generate_keypair,
    sign_challenge,
    verify_challenge,
    EnrollmentCryptoError,
)


class TestEnrollmentCrypto(unittest.TestCase):

    def test_valid_signature(self):
        private_key, public_key = generate_keypair()
        challenge = generate_challenge()
        signature = sign_challenge(private_key, challenge)

        self.assertTrue(
            verify_challenge(public_key, challenge, signature)
        )

    def test_wrong_key(self):
        private_key, _ = generate_keypair()
        _, other_public_key = generate_keypair()

        challenge = generate_challenge()
        signature = sign_challenge(private_key, challenge)

        self.assertFalse(
            verify_challenge(other_public_key, challenge, signature)
        )

    def test_modified_challenge(self):
        private_key, public_key = generate_keypair()
        challenge = generate_challenge()
        signature = sign_challenge(private_key, challenge)

        self.assertFalse(
            verify_challenge(
                public_key,
                generate_challenge(),
                signature,
            )
        )

    def test_invalid_signature(self):
        _, public_key = generate_keypair()

        self.assertFalse(
            verify_challenge(
                public_key,
                generate_challenge(),
                "invalid",
            )
        )

    def test_unique_challenges(self):
        self.assertNotEqual(
            generate_challenge(),
            generate_challenge(),
        )

    def test_encoding_roundtrip(self):
        value = bytes(range(32))
        self.assertEqual(
            decode_bytes(encode_bytes(value), 32),
            value,
        )

    def test_reject_noncanonical_encoding(self):
        with self.assertRaises(EnrollmentCryptoError):
            decode_bytes("AAAA=", 32)


if __name__ == "__main__":
    unittest.main()
