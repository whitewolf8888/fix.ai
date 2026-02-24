"""Marketing and onboarding endpoints."""

import csv
import io
import json
from typing import Dict

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.db.analytics_store import AnalyticsStore
from app.dependencies import get_analytics_store, get_pilot_store, get_settings
from app.services.analytics import track_event
from app.services.auth import require_roles
from app.db.pilot_store import PilotStore, PilotRecord
from app.core.config import Settings
from datetime import datetime


router = APIRouter(prefix="/api/marketing", tags=["Marketing"])


class TrackEventRequest(BaseModel):
    """Track a marketing event."""

    event: str = Field(..., min_length=2)
    properties: Dict = Field(default_factory=dict)


class LeadRequest(BaseModel):
    """Pilot onboarding lead submission."""

    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    company: str = Field(default="")
    team_size: str = Field(default="")
    use_case: str = Field(default="")


@router.post("/track")
async def track_marketing_event(
    payload: TrackEventRequest,
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> dict:
    """Record a marketing event."""
    await track_event(
        analytics_store,
        payload.event,
        payload.properties,
    )
    return {"status": "ok"}


@router.post("/lead")
async def submit_lead(
    payload: LeadRequest,
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    pilot_store: PilotStore = Depends(get_pilot_store),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Record a pilot onboarding lead."""
    await track_event(
        analytics_store,
        "lead_submit",
        {
            "name": payload.name,
            "email": payload.email,
            "company": payload.company,
            "team_size": payload.team_size,
            "use_case": payload.use_case,
        },
    )

    if _should_auto_pilot(payload, settings):
        pilot_id = f"lead:{payload.email}"
        record = PilotRecord(
            pilot_id=pilot_id,
            lead_email=payload.email,
            company=payload.company or payload.name,
            status="new",
            notes=payload.use_case,
            last_reminded_at=None,
            reminder_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await pilot_store.upsert(record)
        await track_event(
            analytics_store,
            "pilot_auto_created",
            {"email": payload.email, "company": payload.company},
        )
    return {"status": "received"}


def _should_auto_pilot(payload: LeadRequest, settings: Settings) -> bool:
    if not settings.AUTO_PILOT_ENABLED:
        return False
    if settings.AUTO_PILOT_ALLOWED_DOMAINS:
        domain = payload.email.split("@")[-1].lower()
        allowed = [d.strip().lower() for d in settings.AUTO_PILOT_ALLOWED_DOMAINS.split(",") if d.strip()]
        if allowed and domain not in allowed:
            return False
    try:
        team_size = int(payload.team_size) if payload.team_size else 0
    except ValueError:
        team_size = 0
    if settings.AUTO_PILOT_MIN_TEAM_SIZE and team_size < settings.AUTO_PILOT_MIN_TEAM_SIZE:
        return False
    return True


@router.get("/leads")
async def list_leads(
    limit: int = 100,
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """List pilot leads (admin only)."""
    events = await analytics_store.list_events("lead_submit", limit=limit)
    leads = []
    for event in events:
        meta = event.get("metadata", {})
        leads.append(
            {
                "id": event.get("event_id"),
                "created_at": event.get("created_at"),
                "name": meta.get("name", ""),
                "email": meta.get("email", ""),
                "company": meta.get("company", ""),
                "team_size": meta.get("team_size", ""),
                "use_case": meta.get("use_case", ""),
            }
        )
    return {"total": len(leads), "leads": leads}


    @router.get("/leads/export")
    async def export_leads(
        format: str = "csv",
        limit: int = 500,
        analytics_store: AnalyticsStore = Depends(get_analytics_store),
        _user=Depends(require_roles(["admin"]))
    ) -> Response:
        """Export leads to CSV or JSON (admin only)."""
        events = await analytics_store.list_events("lead_submit", limit=limit)
        leads = []
        for event in events:
            meta = event.get("metadata", {})
            leads.append(
                {
                    "id": event.get("event_id"),
                    "created_at": event.get("created_at"),
                    "name": meta.get("name", ""),
                    "email": meta.get("email", ""),
                    "company": meta.get("company", ""),
                    "team_size": meta.get("team_size", ""),
                    "use_case": meta.get("use_case", ""),
                }
            )

        if format.lower() == "json":
            return Response(
                content=json.dumps(leads),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=leads.json"},
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "created_at", "name", "email", "company", "team_size", "use_case"])
        for lead in leads:
            writer.writerow([
                lead["id"],
                lead["created_at"],
                lead["name"],
                lead["email"],
                lead["company"],
                lead["team_size"],
                lead["use_case"],
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )
