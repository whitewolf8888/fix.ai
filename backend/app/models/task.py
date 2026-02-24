"""Domain models for task management and scanning."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# === Enums ===
class TaskStatus(str, Enum):
    """Task execution status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    """Vulnerability severity levels."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    MEDIA = "MEDIA"
    INFO = "INFO"


class RemediationStatus(str, Enum):
    """Status of LLM remediation attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# === Domain Models ===
@dataclass
class Finding:
    """A security finding from Semgrep."""
    
    rule_id: str
    rule_name: str
    severity: str
    confidence: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    description: str
    cwe_ids: List[str] = field(default_factory=list)
    owasp_tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PatchReport:
    """AI remediation result for a single finding."""
    
    finding: Finding
    abs_file_path: str
    patched_content: Optional[str] = None
    patch_error: Optional[str] = None
    skipped: bool = False


@dataclass
class ReviewResult:
    """Complete orchestrator pipeline output."""
    
    all_findings: List[Finding]
    patch_reports: List[PatchReport]
    error: Optional[str] = None


@dataclass
class TaskRecord:
    """In-memory/persistent task record."""
    
    task_id: str
    repo_url: str
    branch: str = "main"
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    findings: List[Finding] = field(default_factory=list)
    patch_reports: List[PatchReport] = field(default_factory=list)
    error_message: Optional[str] = None
    
    @classmethod
    def create(cls, task_id: str, repo_url: str, branch: str = "main") -> "TaskRecord":
        """Create a new task record."""
        return cls(task_id=task_id, repo_url=repo_url, branch=branch)
    
    def to_dict(self) -> dict:
        """Convert to dictionary with parsed findings."""
        return {
            "task_id": self.task_id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "findings": [f.to_dict() for f in self.findings],
            "patch_reports": [
                {
                    "finding": pr.finding.to_dict(),
                    "patched_content": pr.patched_content,
                    "patch_error": pr.patch_error,
                    "skipped": pr.skipped,
                }
                for pr in self.patch_reports
            ],
            "error_message": self.error_message,
        }


# === Pydantic Request/Response Models ===
class ScanRequest(BaseModel):
    """Request body for /api/scan."""
    
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to scan")
    auto_remediate: bool = Field(default=True, description="Enable AI auto-remediation")


class ScanResponse(BaseModel):
    """Response from /api/scan."""
    
    task_id: str
    status: str
    poll_url: str


class StatusResponse(BaseModel):
    """Response from /api/status/{task_id}."""
    
    task_id: str
    status: str
    created_at: str
    updated_at: str
    findings: List[dict]
    patch_reports: List[dict]
    error_message: Optional[str]


class FixRequest(BaseModel):
    """Request body for /api/fix."""
    
    repo_name: str = Field(..., description="GitHub repo: owner/repo")
    file_path: str = Field(..., description="File path to patch")
    patched_code: str = Field(..., description="Full patched file content")
    vulnerability_name: str = Field(..., description="Vulnerability identifier")
    base_branch: str = Field(default="main", description="Base branch for PR")


class PRInfo(BaseModel):
    """GitHub Pull Request information."""
    
    pr_number: int
    pr_url: str
    branch_name: str


class FixResponse(BaseModel):
    """Response from /api/fix."""
    
    success: bool
    pull_request: Optional[PRInfo] = None
    error_message: Optional[str] = None


class RemediateRequest(BaseModel):
    """Request body for /api/remediate."""
    
    task_id: str = Field(..., description="Task ID from /api/scan")
    finding_index: int = Field(..., description="Index of finding to remediate")
    file_content: Optional[str] = Field(None, description="Full source file (optional)")


class RemediateResponse(BaseModel):
    """Response from /api/remediate."""
    
    status: str  # "success" | "failed" | "skipped"
    patched_file_content: Optional[str] = None
    patch_error: Optional[str] = None
    tokens_used: Optional[dict] = None


class BulkRemediateRequest(BaseModel):
    """Request body for /api/remediate/bulk."""
    
    task_id: str = Field(..., description="Task ID from /api/scan")
    min_severity: str = Field(default="MEDIUM", description="Minimum severity to remediate")


class BulkRemediateResponse(BaseModel):
    """Response from /api/remediate/bulk."""
    
    succeeded: int
    failed: int
    skipped: int
    results: List[RemediateResponse]


class HealthResponse(BaseModel):
    """Response from /api/health."""
    
    status: str
    version: str
    store_backend: str
    llm_configured: bool
    llm_provider: Optional[str]
    semgrep_available: bool
    github_token_set: bool
    webhook_secret_set: bool
