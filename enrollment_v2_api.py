"""Isolated HTTP API for v2 agent enrollment.

Not connected to the production FastAPI application.
"""

import os
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from enrollment_crypto import decode_bytes, EnrollmentCryptoError
from enrollment_v2 import (
    register_with_key,
    EnrollmentConflictError,
    EnrollmentRegistrationError,
)
from enrollment_store import create_challenge
from enrollment_recoverable import (
    complete_recoverable_enrollment,
    RecoverableEnrollmentError,
)


router = APIRouter(prefix="/api/v2/agents", tags=["Enrollment v2"])


class RegistrationRequest(BaseModel):
    agent_id: str
    hostname: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=1, max_length=64)
    public_key: str = Field(min_length=1, max_length=128)


class CompletionRequest(BaseModel):
    challenge: str
    signature: str
    credential_hash: str


def require_enabled():
    if os.getenv(
        "ARBY_ENROLLMENT_V2_ENABLED", "false"
    ).lower() != "true":
        raise HTTPException(
            status_code=503,
            detail="Enrollment v2 is disabled",
        )


def validate_agent_id(agent_id):
    try:
        if str(UUID(agent_id)) != agent_id:
            raise ValueError("Noncanonical UUID")
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail="Invalid agent identity",
        )
    return agent_id


@router.post("/register", status_code=201)
def register(request: RegistrationRequest):
    require_enabled()
    validate_agent_id(request.agent_id)

    try:
        decode_bytes(request.public_key, 32)
        return register_with_key(
            request.agent_id,
            request.hostname,
            request.platform,
            request.public_key,
        )
    except EnrollmentConflictError:
        raise HTTPException(
            status_code=409,
            detail="Agent identity already registered",
        )
    except (EnrollmentCryptoError, EnrollmentRegistrationError):
        raise HTTPException(
            status_code=422,
            detail="Invalid registration",
        )


@router.post("/{agent_id}/challenge")
def challenge(agent_id: str):
    require_enabled()
    validate_agent_id(agent_id)

    value = create_challenge(agent_id)

    if value is None:
        raise HTTPException(
            status_code=409,
            detail="Enrollment challenge unavailable",
        )

    return {
        "agent_id": agent_id,
        "challenge": value,
    }


@router.post("/{agent_id}/complete")
def complete(agent_id: str, request: CompletionRequest):
    require_enabled()
    validate_agent_id(agent_id)

    try:
        return complete_recoverable_enrollment(
            agent_id,
            request.challenge,
            request.signature,
            request.credential_hash,
        )
    except RecoverableEnrollmentError:
        raise HTTPException(
            status_code=409,
            detail="Enrollment could not be completed",
        )
