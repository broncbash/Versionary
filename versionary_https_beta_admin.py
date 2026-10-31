"""Administrator-only agent lifecycle routes for isolated HTTPS beta."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from admin_auth import require_admin
from agent_registry import approve_agent, revoke_agent

router = APIRouter(
    prefix="/api/v1/admin/agents",
    tags=["Versionary HTTPS beta administration"],
)


@router.post("/{agent_id}/approve")
def approve(
    agent_id: UUID,
    _: None = Depends(require_admin),
):
    """Approve a registered agent after administrator review."""
    if not approve_agent(str(agent_id)):
        raise HTTPException(
            status_code=409,
            detail="Agent cannot be approved",
        )

    return {
        "agent_id": str(agent_id),
        "status": "approved",
    }


@router.post("/{agent_id}/revoke")
def revoke(
    agent_id: UUID,
    _: None = Depends(require_admin),
):
    """Permanently revoke an agent identity."""
    if not revoke_agent(str(agent_id)):
        raise HTTPException(
            status_code=409,
            detail="Agent cannot be revoked",
        )

    return {
        "agent_id": str(agent_id),
        "status": "revoked",
    }
