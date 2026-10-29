"""Ed25519 proof-of-possession verification for enrollment."""

from enrollment_crypto import verify_challenge
from enrollment_store import get_active_challenge


def verify_enrollment_proof(agent_id, challenge, signature):
    """Verify a signature against the agent's active challenge.

    This function is read-only. It does not consume a challenge
    or issue credentials. It must not be used alone to authorize
    enrollment completion.
    """

    if not all(
        isinstance(value, str) and value
        for value in (agent_id, challenge, signature)
    ):
        return False

    active = get_active_challenge(agent_id)

    if active is None:
        return False

    if active["challenge"] != challenge:
        return False

    return verify_challenge(
        active["public_key"],
        challenge,
        signature,
    )
