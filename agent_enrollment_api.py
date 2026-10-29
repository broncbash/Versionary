"""Administrator-controlled agent credential issuance endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from admin_auth import require_admin
from agent_registry import issue_agent_credential


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("/{agent_id}/credential", status_code=201)
def create_agent_credential(
    agent_id: UUID,
    _: None = Depends(require_admin),
):
    """Issue a one-time credential to an approved agent (admin only)."""

    token = issue_agent_credential(str(agent_id))

    if token is None:
        raise HTTPException(
            status_code=409,
            detail="Agent is not eligible for credential issuance",
        )

    return {
        "agent_id": str(agent_id),
        "token": token,
    }
