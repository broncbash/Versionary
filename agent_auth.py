import hashlib
import hmac
import secrets


def generate_agent_token() -> str:
    """Generate a cryptographically secure agent token."""
    return secrets.token_urlsafe(32)


def hash_agent_token(token: str) -> str:
    """Hash an agent token for database storage."""
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def verify_agent_token(
    token: str,
    stored_hash: str,
) -> bool:
    """Verify a token using constant-time comparison."""
    if not token or not stored_hash:
        return False

    calculated_hash = hash_agent_token(token)

    return hmac.compare_digest(
        calculated_hash,
        stored_hash,
    )
