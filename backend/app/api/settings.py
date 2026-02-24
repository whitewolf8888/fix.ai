"""Settings endpoints for admin configuration."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db.settings_store import SettingsStore
from app.dependencies import get_settings_store
from app.services.auth import require_roles


router = APIRouter(prefix="/api/settings", tags=["Settings"])


class ReminderDaysRequest(BaseModel):
    """Reminder schedule update request."""

    reminder_days: str = Field(..., min_length=1)


@router.get("/pilot-reminder-days")
async def get_pilot_reminder_days(
    settings_store: SettingsStore = Depends(get_settings_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Get current pilot reminder schedule."""
    value = await settings_store.get_value("pilot_reminder_days")
    return {"reminder_days": value}


@router.post("/pilot-reminder-days")
async def set_pilot_reminder_days(
    payload: ReminderDaysRequest,
    settings_store: SettingsStore = Depends(get_settings_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Set pilot reminder schedule."""
    await settings_store.set_value("pilot_reminder_days", payload.reminder_days)
    return {"status": "updated", "reminder_days": payload.reminder_days}
