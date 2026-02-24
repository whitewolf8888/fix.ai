"""Pilot workflow models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PilotCreateRequest(BaseModel):
    """Create a pilot entry."""

    lead_email: str = Field(..., min_length=5)
    company: str = Field(default="")
    status: str = Field(default="new")
    notes: str = Field(default="")


class PilotUpdateRequest(BaseModel):
    """Update a pilot status."""

    status: str = Field(..., min_length=2)
    notes: str = Field(default="")


class PilotResponse(BaseModel):
    """Pilot record response."""

    pilot_id: str
    lead_email: str
    company: str
    status: str
    notes: str
    last_reminded_at: Optional[datetime]
    reminder_count: int
    created_at: datetime
    updated_at: datetime


class PilotListResponse(BaseModel):
    """List pilots."""

    total: int
    pilots: list[PilotResponse]
