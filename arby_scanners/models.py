from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class PackageUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    installed: str = Field(min_length=1, max_length=128)
    available: str = Field(min_length=1, max_length=128)
    repository: str | None = Field(default=None, max_length=256)

class ScanResult(BaseModel):
    node: str
    status: Literal["success", "error"]
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    count: int | None
    packages: list[PackageUpdate] = Field(default_factory=list)
    error: str | None = None
