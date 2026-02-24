"""License verification service."""

from datetime import datetime
from typing import Dict, Tuple

from app.core.logging import logger
from app.db.license_store import LicenseStore, LicenseRecord


async def verify_license_key(
    store: LicenseStore,
    license_key: str,
    owner_email: str,
    ip_address: str,
    user_agent: str,
    client_metadata: Dict,
    track_new_ips: bool,
) -> Tuple[bool, bool, bool]:
    """Verify license key and record IP if new.

    Returns:
        (is_active, is_new_ip, is_violation)
    """
    record = await store.get_license(license_key)
    if not record:
        logger.warning(
            "[License] Invalid key attempt",
            extra={"key": license_key, "ip": ip_address, "ua": user_agent},
        )
        return False, False, False

    owner_email = record.owner_email or owner_email
    is_active = record.status.lower() == "active"
    if not is_active:
        logger.warning(
            "[License] Revoked key used",
            extra={"key": license_key, "ip": ip_address, "ua": user_agent},
        )
        return False, False, False

    logger.info(
        "[License] Access",
        extra={"key": license_key, "ip": ip_address, "ua": user_agent, "meta": client_metadata},
    )

    is_new_ip = False
    is_violation = False
    if track_new_ips:
        result = await store.record_ip(license_key, ip_address)
        is_new_ip = result["new_ip"]
        if result["exceeded"]:
            is_violation = True
            if record.soft_lock:
                logger.warning(
                    "[License] Potential license violation",
                    extra={"key": license_key, "ip": ip_address, "owner": owner_email},
                )
            else:
                await store.update_status(license_key, "revoked")
                logger.warning(
                    "[License] License revoked due to IP limit",
                    extra={"key": license_key, "ip": ip_address, "owner": owner_email},
                )
                return False, is_new_ip, True

    return True, is_new_ip, is_violation


def build_bootstrap_record(license_key: str, owner_email: str) -> LicenseRecord:
    """Create a bootstrap license record."""
    now = datetime.utcnow()
    return LicenseRecord(
        license_key=license_key,
        owner_email=owner_email or "unknown",
        status="active",
        allowed_ips=[],
        ip_history=[],
        max_ips=0,
        soft_lock=True,
        created_at=now,
        updated_at=now,
    )
