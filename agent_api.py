"""Agent registration and administrator-controlled lifecycle endpoints."""

import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from admin_auth import require_admin
from agent_feature_flags import registration_enabled, reporting_enabled
from agent_registry import approve_agent, register_agent, revoke_agent

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentRegistration(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=1, max_length=64)
    agent_id: UUID

    @field_validator("hostname", "platform")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be blank")
        return value


@router.get("/status")
def agent_api_status():
    """Report the current agent API configuration."""
    return {
        "service": "ARBY PATCH COMMAND Agent API",
        "status": "development",
        "registration_enabled": registration_enabled(),
        "reporting_enabled": reporting_enabled(),
    }


@router.post("/register", status_code=201)
def register_new_agent(request: AgentRegistration):
    """Register an agent for manual approval."""
    if not registration_enabled():
        raise HTTPException(
            status_code=503,
            detail="Agent registration is disabled",
        )
    try:
        agent_id = register_agent(
            hostname=request.hostname,
            platform=request.platform,
            agent_id=str(request.agent_id),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Agent identity already registered",
        ) from None

    return {"agent_id": agent_id, "status": "pending"}


@router.post("/{agent_id}/approve")
def approve_registered_agent(
    agent_id: UUID,
    _: None = Depends(require_admin),
):
    """Approve a pending agent. Administrator only."""
    if not approve_agent(str(agent_id)):
        raise HTTPException(
            status_code=409,
            detail="Agent cannot be approved",
        )
    return {"agent_id": str(agent_id), "status": "approved"}


@router.post("/{agent_id}/revoke")
def revoke_registered_agent(
    agent_id: UUID,
    _: None = Depends(require_admin),
):
    """Permanently revoke an agent identity. Administrator only."""
    if not revoke_agent(str(agent_id)):
        raise HTTPException(
            status_code=409,
            detail="Agent cannot be revoked",
        )
    return {"agent_id": str(agent_id), "status": "revoked"}

