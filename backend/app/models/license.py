"""License API models."""

from datetime import datetime
from typing import List, Dict

from pydantic import BaseModel, Field


class LicenseCreateRequest(BaseModel):
    """Create or update a license."""

    license_key: str = Field(..., min_length=5)
    owner_email: str = Field(..., min_length=3)
    status: str = Field(default="active")
    allowed_ips: List[str] = Field(default_factory=list)
    max_ips: int = Field(default=0, ge=0)
    soft_lock: bool = Field(default=True)


class LicenseResponse(BaseModel):
    """License response."""

    license_key: str
    owner_email: str
    status: str
    allowed_ips: List[str]
    ip_history: List[Dict]
    max_ips: int
    soft_lock: bool
    created_at: datetime
    updated_at: datetime


class LicenseListResponse(BaseModel):
    """List of licenses."""

    total: int
    licenses: List[LicenseResponse]
