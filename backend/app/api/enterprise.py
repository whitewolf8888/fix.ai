"""Enterprise API Endpoints for Team Management, Analytics, and Export."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import (
    User, Team, UserRole, SecurityFinding, Patch, NotificationPreference, TeamRepository
)
from app.services.team_management import TeamManager, UserManager, TokenManager, AccessController
from app.services.analytics import EnterpriseAnalytics, AdvancedFilter
from app.services.export_service import CSVExporter, JSONExporter, ComplianceReportGenerator

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


# ============================================================================
# Team Management Endpoints
# ============================================================================

@router.post("/teams")
def create_team(name: str, description: str = "", db: Session = Depends(get_db)):
    """Create a new team."""
    team_manager = TeamManager(db)
    team = team_manager.create_team(name, description)
    return {"team_id": team.id, "name": team.name}


@router.get("/teams/{team_id}")
def get_team_info(team_id: str, db: Session = Depends(get_db)):
    """Get team information."""
    team_manager = TeamManager(db)
    team = team_manager.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    stats = team_manager.get_team_stats(team_id)
    return stats


@router.post("/teams/{team_id}/upgrade")
def upgrade_subscription(team_id: str, tier: str, db: Session = Depends(get_db)):
    """Upgrade team subscription."""
    team_manager = TeamManager(db)
    
    try:
        from app.db.models import SubscriptionTier
        tier_enum = SubscriptionTier[tier.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    team = team_manager.upgrade_subscription(team_id, tier_enum)
    return {"tier": team.subscription_tier.value, "max_repos": team.max_repos}


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.post("/users")
def create_user(
    email: str,
    username: str,
    password: str,
    team_id: str,
    full_name: str = "",
    role: str = "developer",
    db: Session = Depends(get_db)
):
    """Create a new user."""
    user_manager = UserManager(db)
    
    try:
        role_enum = UserRole[role.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = user_manager.create_user(email, username, password, team_id, full_name, role_enum)
    token = TokenManager.create_token(user)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "token": token
    }


@router.post("/auth/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    """Authenticate user and get token."""
    user_manager = UserManager(db)
    user = user_manager.authenticate(email, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = TokenManager.create_token(user)
    return {"token": token, "user_id": user.id, "role": user.role.value}


@router.post("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    new_role: str,
    authorized_by: str,
    db: Session = Depends(get_db)
):
    """Change user role (Admin only)."""
    user_manager = UserManager(db)
    
    try:
        role_enum = UserRole[new_role.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = user_manager.change_role(user_id, role_enum, authorized_by)
    return {"user_id": user.id, "role": user.role.value}


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/analytics/dashboard/{team_id}")
def get_dashboard(team_id: str, db: Session = Depends(get_db)):
    """Get team dashboard metrics."""
    analytics = EnterpriseAnalytics(db)
    metrics = analytics.get_team_metrics(team_id)
    return metrics


@router.get("/analytics/severity/{team_id}")
def get_severity_distribution(team_id: str, db: Session = Depends(get_db)):
    """Get findings by severity."""
    analytics = EnterpriseAnalytics(db)
    distribution = analytics.get_severity_distribution(team_id)
    return distribution


# ============================================================================
# Filtering Endpoints
# ============================================================================

@router.get("/findings/filter/{team_id}")
def filter_findings(
    team_id: str,
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    days_old: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Advanced filtering of findings."""
    filter_service = AdvancedFilter(db)
    
    severity_list = severity.split(",") if severity else None
    status_list = status.split(",") if status else None
    language_list = language.split(",") if language else None
    
    findings = filter_service.filter_findings(
        team_id,
        severity=severity_list,
        status=status_list,
        language=language_list,
        days_old=days_old
    )
    
    return {
        "total": len(findings),
        "findings": [
            {
                "id": f.id,
                "rule": f.rule_id,
                "severity": f.severity.value,
                "status": f.status
            }
            for f in findings[:100]  # Limit to 100
        ]
    }


# ============================================================================
# Export Endpoints
# ============================================================================

@router.get("/export/findings/{team_id}/csv")
def export_findings_csv(team_id: str, db: Session = Depends(get_db)):
    """Export findings to CSV."""
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.team_id == team_id
    ).all()
    
    csv_content = CSVExporter.export_findings(findings, team_id)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=findings.csv"}
    )


@router.get("/export/findings/{team_id}/json")
def export_findings_json(team_id: str, db: Session = Depends(get_db)):
    """Export findings to JSON."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.team_id == team_id
    ).all()
    
    json_content = JSONExporter.export_findings(findings, team)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=findings.json"}
    )


@router.get("/export/patches/{team_id}/csv")
def export_patches_csv(team_id: str, db: Session = Depends(get_db)):
    """Export patches to CSV."""
    patches = db.query(Patch).filter(Patch.team_id == team_id).all()
    csv_content = CSVExporter.export_patches(patches)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patches.csv"}
    )


@router.get("/export/compliance/{team_id}/gdpr")
def export_gdpr_report(team_id: str, db: Session = Depends(get_db)):
    """Export GDPR compliance report."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.team_id == team_id
    ).all()
    
    report = ComplianceReportGenerator.generate_gdpr_report(findings, team)
    return report


@router.get("/export/compliance/{team_id}/hipaa")
def export_hipaa_report(team_id: str, db: Session = Depends(get_db)):
    """Export HIPAA compliance report."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.team_id == team_id
    ).all()
    
    report = ComplianceReportGenerator.generate_hipaa_report(findings, team)
    return report


@router.get("/export/compliance/{team_id}/soc2")
def export_soc2_report(team_id: str, db: Session = Depends(get_db)):
    """Export SOC2 compliance report."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    findings = db.query(SecurityFinding).filter(
        SecurityFinding.team_id == team_id
    ).all()
    
    analytics = EnterpriseAnalytics(db)
    metrics = analytics.get_team_metrics(team_id)
    
    report = ComplianceReportGenerator.generate_soc2_report(findings, team, metrics)
    return report


# ============================================================================
# Notification Preferences
# ============================================================================

@router.post("/notifications/preferences/{user_id}")
def set_notification_preferences(
    user_id: str,
    email_on_findings: bool = True,
    email_on_critical: bool = True,
    slack_enabled: bool = False,
    slack_webhook_url: Optional[str] = None,
    daily_digest: bool = True,
    db: Session = Depends(get_db)
):
    """Set notification preferences for user."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    
    if prefs:
        prefs.email_on_findings = email_on_findings
        prefs.email_on_critical = email_on_critical
        prefs.slack_enabled = slack_enabled
        prefs.slack_webhook_url = slack_webhook_url
        prefs.daily_digest = daily_digest
    else:
        prefs = NotificationPreference(
            id=str(__import__('uuid').uuid4()),
            user_id=user_id,
            email_on_findings=email_on_findings,
            email_on_critical=email_on_critical,
            slack_enabled=slack_enabled,
            slack_webhook_url=slack_webhook_url,
            daily_digest=daily_digest
        )
        db.add(prefs)
    
    db.commit()
    return {"status": "preferences updated"}


@router.get("/notifications/preferences/{user_id}")
def get_notification_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get notification preferences."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    
    return {
        "email_on_findings": prefs.email_on_findings,
        "email_on_critical": prefs.email_on_critical,
        "slack_enabled": prefs.slack_enabled,
        "daily_digest": prefs.daily_digest
    }


# ============================================================================
# Repository Management
# ============================================================================

@router.post("/repositories/{team_id}")
def add_repository(
    team_id: str,
    repo_url: str,
    repo_name: str,
    default_branch: str = "main",
    description: str = "",
    db: Session = Depends(get_db)
):
    """Add repository to team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if len(team.repositories) >= team.max_repos:
        raise HTTPException(status_code=403, detail="Repository limit reached for team tier")
    
    repo = TeamRepository(
        id=str(__import__('uuid').uuid4()),
        team_id=team_id,
        repo_url=repo_url,
        repo_name=repo_name,
        default_branch=default_branch,
        description=description
    )
    
    db.add(repo)
    db.commit()
    db.refresh(repo)
    
    return {"repository_id": repo.id, "name": repo.repo_name}


@router.get("/repositories/{team_id}")
def list_repositories(team_id: str, db: Session = Depends(get_db)):
    """List team repositories."""
    repos = db.query(TeamRepository).filter(
        TeamRepository.team_id == team_id,
        TeamRepository.is_active == True
    ).all()
    
    return {
        "total": len(repos),
        "repositories": [
            {
                "id": r.id,
                "name": r.repo_name,
                "url": r.repo_url,
                "last_scan": r.last_scan_at
            }
            for r in repos
        ]
    }
