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



    # ============================================================================
    # ENTERPRISE NOTIFICATION FEATURES
    # ============================================================================

    import requests
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from typing import List, Optional
    from datetime import datetime
    import os


    class EmailNotifier:
        """Enterprise email notifier for security findings and patches."""
    
        def __init__(self, settings: Settings = None):
            if settings:
                self.smtp_host = settings.SMTP_HOST or "smtp.gmail.com"
                self.smtp_port = settings.SMTP_PORT or 587
                self.sender_email = settings.SMTP_FROM or "noreply@vulnsentinel.ai"
                self.sender_password = settings.SMTP_PASSWORD or ""
            else:
                self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
                self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
                self.sender_email = os.getenv("SENDER_EMAIL", "noreply@vulnsentinel.ai")
                self.sender_password = os.getenv("SENDER_PASSWORD", "")
    
        def send_patch_approval_request(self, recipient_email: str, finding_title: str, confidence: float) -> bool:
            """Send patch approval request email."""
            try:
                subject = f"📋 Patch Approval Required: {finding_title}"
                body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif;">
                        <h2>📋 Security Patch Approval</h2>
                        <p>A security patch has been generated and requires approval:</p>
                        <p><strong>Finding:</strong> {finding_title}</p>
                        <p><strong>Confidence Score:</strong> {confidence * 100:.1f}%</p>
                        <p><a href="http://localhost:3000/security">Review Patch →</a></p>
                    </body>
                </html>
                """
                return self._send_email(recipient_email, subject, body)
            except Exception as e:
                logger.warning(f"Failed to send patch approval email: {str(e)}")
                return False
    
        def send_daily_digest(self, recipient_email: str, summary: dict, team_name: str) -> bool:
            """Send daily vulnerability digest."""
            try:
                subject = f"📊 VulnSentinel Daily Digest - {datetime.now().strftime('%Y-%m-%d')}"
                body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif;">
                        <h2>📊 VulnSentinel Daily Digest</h2>
                        <p><strong>Team:</strong> {team_name}</p>
                        <table border="1" cellpadding="10">
                            <tr style="background-color: #f0f0f0;">
                                <th>Metric</th>
                                <th>Count</th>
                            </tr>
                            <tr><td>New Findings</td><td>{summary.get('new_findings', 0)}</td></tr>
                            <tr><td>Critical Issues</td><td>{summary.get('critical', 0)}</td></tr>
                            <tr><td>Patched Today</td><td>{summary.get('patched', 0)}</td></tr>
                            <tr><td>Scans Completed</td><td>{summary.get('scans', 0)}</td></tr>
                        </table>
                    </body>
                </html>
                """
                return self._send_email(recipient_email, subject, body)
            except Exception as e:
                logger.warning(f"Failed to send daily digest: {str(e)}")
                return False
    
        def _send_email(self, to_email: str, subject: str, body: str) -> bool:
            """Send email via SMTP."""
            try:
                if not self.sender_password:
                    logger.warning("SENDER_PASSWORD not configured")
                    return False
            
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = self.sender_email
                msg["To"] = to_email
                msg.attach(MIMEText(body, "html"))
            
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            
                return True
            except Exception as e:
                logger.warning(f"SMTP error: {str(e)}")
                return False


    class SlackNotifier:
        """Enterprise Slack notifier for security findings."""
    
        def __init__(self, webhook_url: str):
            self.webhook_url = webhook_url
    
        def send_finding_alert(self, finding_title: str, severity: str, file_path: str, lines: str) -> bool:
            """Send finding alert to Slack."""
            try:
                color_map = {
                    "critical": "#dc2626",
                    "high": "#f97316",
                    "medium": "#eab308",
                    "low": "#3b82f6"
                }
            
                payload = {
                    "text": f"🔒 {severity.upper()} Vulnerability Found",
                    "attachments": [{
                        "color": color_map.get(severity, "#808080"),
                        "fields": [
                            {"title": "Title", "value": finding_title, "short": False},
                            {"title": "File", "value": file_path, "short": True},
                            {"title": "Lines", "value": lines, "short": True}
                        ],
                        "ts": int(datetime.now().timestamp())
                    }]
                }
                response = requests.post(self.webhook_url, json=payload, timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Slack notification failed: {str(e)}")
                return False
    
        def send_critical_alert(self, findings_count: int, team_name: str) -> bool:
            """Send critical vulnerabilities alert to Slack."""
            try:
                payload = {
                    "text": "🚨 CRITICAL ALERT",
                    "attachments": [{
                        "color": "#dc2626",
                        "fields": [
                            {"title": "Team", "value": team_name, "short": True},
                            {"title": "Critical Findings", "value": str(findings_count), "short": True}
                        ],
                        "footer": "VulnSentinel"
                    }]
                }
                response = requests.post(self.webhook_url, json=payload, timeout=5)
                return response.status_code == 200
            except Exception as e:
                logger.warning(f"Slack critical alert failed: {str(e)}")
                return False
