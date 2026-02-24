"""Notification helpers for alerts."""

import json
import smtplib
from email.message import EmailMessage
from urllib import request as urlrequest

from app.core.config import Settings
from app.core.logging import logger


def _send_email(settings: Settings, subject: str, body: str) -> None:
    if not settings.ALERT_EMAIL_ENABLED:
        return
    if not settings.SMTP_HOST or not settings.ALERT_EMAIL_RECIPIENTS:
        logger.warning("[Notify] SMTP not configured; skipping email")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER or "no-reply@vulnsentinel"
    msg["To"] = ",".join(settings.ALERT_EMAIL_RECIPIENTS.split(","))
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def _send_email_to(settings: Settings, to_email: str, subject: str, body: str) -> None:
    if not settings.PILOT_EMAIL_ENABLED:
        return
    if not settings.SMTP_HOST or not to_email:
        logger.warning("[Notify] SMTP not configured; skipping pilot email")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.PILOT_EMAIL_FROM or settings.SMTP_FROM or settings.SMTP_USER or "no-reply@vulnsentinel"
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def _send_slack(settings: Settings, message: str) -> None:
    if not settings.SLACK_WEBHOOK_URL:
        return

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urlrequest.Request(
        settings.SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=5):
            pass
    except Exception as exc:
        logger.warning(f"[Notify] Slack webhook failed: {exc}")


def send_license_alert(settings: Settings, license_key: str, ip_address: str, owner_email: str, user_agent: str) -> None:
    """Send alert for potential license violation."""
    subject = "VulnSentinel License Alert"
    body = (
        "Potential license violation detected.\n\n"
        f"License Key: {license_key}\n"
        f"Owner: {owner_email}\n"
        f"IP Address: {ip_address}\n"
        f"User-Agent: {user_agent}\n"
    )

    try:
        _send_email(settings, subject, body)
    except Exception as exc:
        logger.warning(f"[Notify] Email failed: {exc}")

    _send_slack(settings, f"{subject}: {license_key} at {ip_address}")


def send_pilot_email(settings: Settings, to_email: str, subject: str, body: str) -> None:
    """Send pilot-related email."""
    try:
        _send_email_to(settings, to_email, subject, body)
    except Exception as exc:
        logger.warning(f"[Notify] Pilot email failed: {exc}")


def send_pilot_reminder(settings: Settings, to_email: str, company: str) -> None:
    """Send pilot reminder email."""
    subject = settings.PILOT_REMINDER_SUBJECT or "VulnSentinel Pilot Reminder"
    body = (
        "Hi there,\n\n"
        f"Just checking in on your VulnSentinel pilot for {company or 'your team'}. "
        "We are ready to help you run your first scans and review results.\n\n"
        "Reply to this email with a time that works for you.\n\n"
        "Thanks,\nVulnSentinel Team\n"
    )
    send_pilot_email(settings, to_email, subject, body)
