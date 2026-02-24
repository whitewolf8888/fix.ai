"""Pilot workflow endpoints."""

import csv
import io
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.pilot_store import PilotStore, PilotRecord
from app.dependencies import get_pilot_store, get_settings, get_analytics_store, get_settings_store
from app.models.pilot import PilotCreateRequest, PilotUpdateRequest, PilotResponse, PilotListResponse
from app.services.auth import require_roles
from app.services.notifications import send_pilot_reminder
from app.services.pilot_reminders import run_scheduled_reminders
from app.db.analytics_store import AnalyticsStore
from app.services.analytics import track_event
from app.core.config import Settings
from app.db.settings_store import SettingsStore


router = APIRouter(prefix="/api/pilots", tags=["Pilots"])


@router.post("")
async def create_pilot(
    payload: PilotCreateRequest,
    store: PilotStore = Depends(get_pilot_store),
    _user=Depends(require_roles(["admin"]))
) -> PilotResponse:
    """Create a new pilot entry."""
    record = PilotRecord(
        pilot_id=str(uuid.uuid4()),
        lead_email=payload.lead_email,
        company=payload.company,
        status=payload.status,
        notes=payload.notes,
        last_reminded_at=None,
        reminder_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await store.upsert(record)
    return PilotResponse(**record.__dict__)


@router.get("")
async def list_pilots(
    store: PilotStore = Depends(get_pilot_store),
    _user=Depends(require_roles(["admin"]))
) -> PilotListResponse:
    """List pilots."""
    records = await store.list_all()
    return PilotListResponse(
        total=len(records),
        pilots=[PilotResponse(**r.__dict__) for r in records],
    )


@router.post("/{pilot_id}")
async def update_pilot(
    pilot_id: str,
    payload: PilotUpdateRequest,
    store: PilotStore = Depends(get_pilot_store),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    _user=Depends(require_roles(["admin"]))
) -> PilotResponse:
    """Update a pilot status."""
    record = await store.get(pilot_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot not found")
    record.status = payload.status
    record.notes = payload.notes
    record.updated_at = datetime.utcnow()
    await store.upsert(record)
    await track_event(
        analytics_store,
        "pilot_status_update",
        {"pilot_id": record.pilot_id, "status": record.status},
    )
    return PilotResponse(**record.__dict__)


@router.post("/{pilot_id}/remind")
async def remind_pilot(
    pilot_id: str,
    store: PilotStore = Depends(get_pilot_store),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Send a pilot reminder email (admin only)."""
    record = await store.get(pilot_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot not found")
    send_pilot_reminder(settings, record.lead_email, record.company)
    record.reminder_count = (record.reminder_count or 0) + 1
    record.last_reminded_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    await store.upsert(record)
    await track_event(
        analytics_store,
        "pilot_reminder_sent",
        {"pilot_id": record.pilot_id, "email": record.lead_email},
    )
    return {"status": "sent"}


@router.post("/reminders/run")
async def run_reminders(
    store: PilotStore = Depends(get_pilot_store),
    settings: Settings = Depends(get_settings),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    settings_store: SettingsStore = Depends(get_settings_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Run scheduled pilot reminders (admin only)."""
    sent = await run_scheduled_reminders(
        settings=settings,
        pilot_store=store,
        analytics_store=analytics_store,
        settings_store=settings_store,
    )

    return {"sent": sent}


@router.get("/export")
async def export_pilots(
    format: str = "csv",
    store: PilotStore = Depends(get_pilot_store),
    _user=Depends(require_roles(["admin"]))
) -> Response:
    """Export pilots to CSV or JSON (admin only)."""
    records = await store.list_all()
    pilots = [r.__dict__ for r in records]

    if format.lower() == "json":
        return Response(
            content=json.dumps(pilots, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=pilots.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "pilot_id",
        "lead_email",
        "company",
        "status",
        "notes",
        "last_reminded_at",
        "reminder_count",
        "created_at",
        "updated_at",
    ])
    for pilot in pilots:
        writer.writerow(
            [
                pilot.get("pilot_id"),
                pilot.get("lead_email"),
                pilot.get("company"),
                pilot.get("status"),
                pilot.get("notes"),
                pilot.get("last_reminded_at"),
                pilot.get("reminder_count"),
                pilot.get("created_at"),
                pilot.get("updated_at"),
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pilots.csv"},
    )
