"""PostgreSQL database models for enterprise features."""

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, Float, 
    ForeignKey, Table, Enum as SQLEnum, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


# ============================================================================
# Enums
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class SubscriptionTier(str, enum.Enum):
    """Subscription tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SeverityLevel(str, enum.Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ============================================================================
# Team & User Models
# ============================================================================

class Team(Base):
    """Team/Organization."""
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    logo_url = Column(String(500))
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    max_repos = Column(Integer, default=10)
    max_team_members = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="team")
    repositories = relationship("TeamRepository", back_populates="team")
    findings = relationship("SecurityFinding", back_populates="team")
    patches = relationship("Patch", back_populates="team")
    
    def __repr__(self):
        return f"<Team {self.name}>"


class User(Base):
    """User account."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.DEVELOPER)
    avatar_url = Column(String(500))
    is_active = Column(Boolean, default=True, index=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    team = relationship("Team", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"


class APIKey(Base):
    """API keys for programmatic access."""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey {self.name}>"


# ============================================================================
# Repository & Scan Models
# ============================================================================

class TeamRepository(Base):
    """Repository managed by team."""
    __tablename__ = "team_repositories"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), index=True)
    repo_url = Column(String(500), nullable=False)
    repo_name = Column(String(255), nullable=False, index=True)
    default_branch = Column(String(100), default="main")
    description = Column(Text)
    language = Column(String(50))
    is_active = Column(Boolean, default=True, index=True)
    auto_scan_enabled = Column(Boolean, default=True)
    auto_remediate_enabled = Column(Boolean, default=True)
    last_scan_at = Column(DateTime)
    next_scan_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="repositories")
    scans = relationship("Scan", back_populates="repository")
    
    def __repr__(self):
        return f"<Repository {self.repo_name}>"


class Scan(Base):
    """Security scan execution."""
    __tablename__ = "scans"
    
    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("team_repositories.id"), index=True)
    branch = Column(String(100), default="main")
    optimization_mode = Column(String(50), default="balanced")
    status = Column(String(50), index=True)  # queued, processing, completed, failed
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    duration_seconds = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    repository = relationship("TeamRepository", back_populates="scans")
    findings = relationship("SecurityFinding", back_populates="scan")
    
    def __repr__(self):
        return f"<Scan {self.id}>"


class SecurityFinding(Base):
    """Security vulnerability finding."""
    __tablename__ = "security_findings"
    
    id = Column(String, primary_key=True)
    scan_id = Column(String, ForeignKey("scans.id"), index=True)
    team_id = Column(String, ForeignKey("teams.id"), index=True)
    rule_id = Column(String(255), index=True)
    rule_name = Column(String(500))
    severity = Column(SQLEnum(SeverityLevel), index=True)
    file_path = Column(String(500))
    line_start = Column(Integer)
    line_end = Column(Integer)
    code_snippet = Column(Text)
    description = Column(Text)
    cwe_ids = Column(JSON)  # [CWE-123, CWE-456]
    owasp_tags = Column(JSON)  # [A01:2021, A02:2021]
    is_false_positive = Column(Boolean, default=False, index=True)
    is_fixed = Column(Boolean, default=False, index=True)
    assigned_to = Column(String, ForeignKey("users.id"))
    status = Column(String(50), default="open")  # open, in_progress, resolved, wontfix
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)
    
    # Relationships
    scan = relationship("Scan", back_populates="findings")
    team = relationship("Team", back_populates="findings")
    patches = relationship("Patch", back_populates="finding")
    comments = relationship("Comment", back_populates="finding")
    
    def __repr__(self):
        return f"<Finding {self.rule_id}>"


class Patch(Base):
    """AI-generated security patch."""
    __tablename__ = "patches"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), index=True)
    finding_id = Column(String, ForeignKey("security_findings.id"), index=True)
    original_content = Column(Text)
    patched_content = Column(Text)
    confidence_score = Column(Float)  # 0-1
    status = Column(String(50), default="pending")  # pending, approved, applied, rejected
    pr_url = Column(String(500))  # GitHub PR link
    pr_status = Column(String(50))  # open, merged, closed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    merged_at = Column(DateTime)
    
    # Relationships
    team = relationship("Team", back_populates="patches")
    finding = relationship("SecurityFinding", back_populates="patches")
    comments = relationship("Comment", back_populates="patch")
    
    def __repr__(self):
        return f"<Patch {self.id}>"


class Comment(Base):
    """Comments on findings or patches."""
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True)
    finding_id = Column(String, ForeignKey("security_findings.id"), index=True, nullable=True)
    patch_id = Column(String, ForeignKey("patches.id"), index=True, nullable=True)
    author_id = Column(String, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    finding = relationship("SecurityFinding", back_populates="comments")
    patch = relationship("Patch", back_populates="comments")
    
    def __repr__(self):
        return f"<Comment {self.id}>"


# ============================================================================
# Analytics & Reporting Models
# ============================================================================

class ScanStatistic(Base):
    """Daily scan statistics."""
    __tablename__ = "scan_statistics"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), index=True)
    scan_date = Column(String, default=lambda: datetime.utcnow().strftime('%Y-%m-%d'), index=True)
    total_scans = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    avg_scan_time_seconds = Column(Float)
    fixed_count = Column(Integer, default=0)
    false_positive_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Stats {self.scan_date}>"


class AuditLog(Base):
    """Audit trail for compliance."""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    action = Column(String(255), index=True)
    resource_type = Column(String(100))  # User, Finding, Patch, etc
    resource_id = Column(String(255), index=True)
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action}>"


class NotificationPreference(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, index=True)
    email_on_findings = Column(Boolean, default=True)
    email_on_critical = Column(Boolean, default=True)
    slack_enabled = Column(Boolean, default=False)
    slack_webhook_url = Column(String(500))
    slack_channel = Column(String(100))
    daily_digest = Column(Boolean, default=True)
    digest_time = Column(String, default="09:00")  # HH:MM format
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<NotificationPreference user={self.user_id}>"
