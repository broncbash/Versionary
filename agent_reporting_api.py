"""Authenticated agent heartbeat and update-report endpoints."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from agent_feature_flags import reporting_enabled
from agent_registry import (
    authenticate_agent,
    record_agent_heartbeat,
    record_agent_scan,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class ScanReport(BaseModel):
    status: Literal["success", "error"]
    packages: list[Any] = Field(default_factory=list, max_length=5000)
    error: str | None = Field(default=None, max_length=4096)


def require_reporting_enabled() -> None:
    if not reporting_enabled():
        raise HTTPException(
            status_code=503,
            detail="Agent reporting is disabled",
        )


def require_agent_token(agent_id: str, authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Agent authentication required"
        )

    scheme, sep, token = authorization.partition(" ")

    if (
        not sep
        or scheme.lower() != "bearer"
        or not token
        or not authenticate_agent(agent_id, token)
    ):
        raise HTTPException(
            status_code=401, detail="Agent authentication required"
        )

    return token


@router.post("/{agent_id}/heartbeat")
def heartbeat(
    agent_id: UUID,
    authorization: str | None = Header(default=None),
):
    require_reporting_enabled()
    agent_id_str = str(agent_id)
    token = require_agent_token(agent_id_str, authorization)

    if not record_agent_heartbeat(agent_id_str, token):
        raise HTTPException(
            status_code=401, detail="Agent authentication required"
        )

    return {"agent_id": agent_id_str, "status": "ok"}


@router.post("/{agent_id}/report", status_code=201)
def submit_report(
    agent_id: UUID,
    report: ScanReport,
    authorization: str | None = Header(default=None),
):
    require_reporting_enabled()
    agent_id_str = str(agent_id)
    token = require_agent_token(agent_id_str, authorization)

    if not record_agent_scan(
        agent_id_str,
        token,
        report.status,
        report.packages,
        report.error,
    ):
        raise HTTPException(
            status_code=422, detail="Invalid scan report"
        )

    return {"agent_id": agent_id_str, "status": "recorded"}
