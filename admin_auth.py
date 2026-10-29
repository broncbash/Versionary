import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

def authenticate_admin(token: str | None) -> bool:
    """Validate an administrator token against its configured hash."""

    expected_hash = os.environ.get("ARBY_ADMIN_TOKEN_HASH", "")

    if not token or len(expected_hash) != 64:
        return False

    try:
        bytes.fromhex(expected_hash)
    except ValueError:
        return False

    supplied_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    return hmac.compare_digest(
        supplied_hash,
        expected_hash.lower(),
    )

admin_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        admin_bearer
    ),
) -> None:
    """Require valid administrator bearer authentication."""

    if credentials is None or not authenticate_admin(
        credentials.credentials
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
