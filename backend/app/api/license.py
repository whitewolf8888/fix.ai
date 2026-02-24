"""License verification endpoints."""

import csv
import io
import json
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.dependencies import get_settings, get_license_store, get_analytics_store
from app.db.license_store import LicenseStore
from app.db.analytics_store import AnalyticsStore
from app.models.license import LicenseCreateRequest, LicenseResponse, LicenseListResponse
from app.services.license_manager import verify_license_key
from app.services.auth import require_roles
from app.services.analytics import track_event
from app.services.notifications import send_license_alert


router = APIRouter(prefix="/api/license", tags=["License"])


class LicenseVerifyRequest(BaseModel):
    """License verification request."""

    license_key: str = Field(..., min_length=5)
    client_metadata: Dict = Field(default_factory=dict)


@router.post("/verify")
async def verify_license(
    payload: LicenseVerifyRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    store: LicenseStore = Depends(get_license_store),
    analytics_store: AnalyticsStore = Depends(get_analytics_store),
) -> dict:
    """Verify license and record access."""
    if not payload.license_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="license_key required")

    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    is_active, is_new_ip, is_violation = await verify_license_key(
        store=store,
        license_key=payload.license_key,
        owner_email=settings.LICENSE_BOOTSTRAP_OWNER,
        ip_address=ip_address,
        user_agent=user_agent,
        client_metadata=payload.client_metadata,
        track_new_ips=settings.LICENSE_TRACK_NEW_IPS,
    )

    await track_event(
        analytics_store,
        "license_verify",
        {"key": payload.license_key, "ip": ip_address, "status": "active" if is_active else "revoked"},
    )

    if is_new_ip:
        await track_event(
            analytics_store,
            "license_new_ip",
            {"key": payload.license_key, "ip": ip_address},
        )
        record = await store.get_license(payload.license_key)
        owner_email = record.owner_email if record else settings.LICENSE_BOOTSTRAP_OWNER
        if is_violation:
            await track_event(
                analytics_store,
                "license_violation",
                {"key": payload.license_key, "ip": ip_address},
            )
            send_license_alert(settings, payload.license_key, ip_address, owner_email, user_agent)

    return {"status": "active" if is_active else "revoked"}


@router.get("")
async def list_licenses(
    store: LicenseStore = Depends(get_license_store),
    _user=Depends(require_roles(["admin"]))
) -> LicenseListResponse:
    """List all licenses (admin only)."""
    records = await store.list_licenses()
    licenses = [
        LicenseResponse(
            license_key=r.license_key,
            owner_email=r.owner_email,
            status=r.status,
            allowed_ips=r.allowed_ips,
            ip_history=r.ip_history,
            max_ips=r.max_ips,
            soft_lock=r.soft_lock,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]
    return LicenseListResponse(total=len(licenses), licenses=licenses)


@router.post("")
async def create_license(
    payload: LicenseCreateRequest,
    store: LicenseStore = Depends(get_license_store),
    _user=Depends(require_roles(["admin"]))
) -> LicenseResponse:
    """Create or update a license (admin only)."""
    from app.services.license_manager import build_bootstrap_record

    record = build_bootstrap_record(payload.license_key, payload.owner_email)
    record.status = payload.status
    record.allowed_ips = payload.allowed_ips
    record.max_ips = payload.max_ips
    record.soft_lock = payload.soft_lock
    await store.upsert_license(record)
    return LicenseResponse(
        license_key=record.license_key,
        owner_email=record.owner_email,
        status=record.status,
        allowed_ips=record.allowed_ips,
        ip_history=record.ip_history,
        max_ips=record.max_ips,
        soft_lock=record.soft_lock,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/{license_key}/revoke")
async def revoke_license(
    license_key: str,
    store: LicenseStore = Depends(get_license_store),
    _user=Depends(require_roles(["admin"]))
) -> dict:
    """Revoke a license (admin only)."""
    updated = await store.update_status(license_key, "revoked")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    return {"status": "revoked"}


@router.get("/{license_key}/ip-history")
async def export_ip_history(
    license_key: str,
    format: str = "json",
    store: LicenseStore = Depends(get_license_store),
    _user=Depends(require_roles(["admin"]))
) -> Response:
    """Export IP history for a license as JSON or CSV (admin only)."""
    record = await store.get_license(license_key)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ip", "first_seen", "last_seen", "count"])
        for entry in record.ip_history:
            writer.writerow([
                entry.get("ip", ""),
                entry.get("first_seen", ""),
                entry.get("last_seen", ""),
                entry.get("count", 0),
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={license_key}_ip_history.csv"},
        )

    return Response(
        content=json.dumps(record.ip_history),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={license_key}_ip_history.json"},
    )
