"""Analytics helpers."""

import uuid
from datetime import datetime
from typing import Dict

from app.db.analytics_store import AnalyticsStore, AnalyticsEvent


async def track_event(analytics_store: AnalyticsStore, event_type: str, metadata: Dict) -> None:
    """Record an analytics event."""
    event = AnalyticsEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        created_at=datetime.utcnow(),
        metadata=metadata,
    )
    await analytics_store.record_event(event)



    # ============================================================================
    # ENTERPRISE ANALYTICS FEATURES
    # ============================================================================

    from sqlalchemy.orm import Session
    from sqlalchemy import func
    from datetime import timedelta
    from typing import List, Optional
    from collections import defaultdict


    class EnterpriseAnalytics:
        """Enterprise analytics and dashboard metrics."""
    
        def __init__(self, db: Session):
            self.db = db
    
        def get_team_metrics(self, team_id: str) -> Dict:
            """Get key metrics for team dashboard."""
            from app.db.models import SecurityFinding, SeverityLevel, Patch, TeamRepository
        
            # Query critical findings
            critical = self.db.query(SecurityFinding).filter(
                SecurityFinding.team_id == team_id,
                SecurityFinding.severity == SeverityLevel.CRITICAL,
                SecurityFinding.is_fixed == False
            ).count()
        
            # Query total findings
            total = self.db.query(SecurityFinding).filter(
                SecurityFinding.team_id == team_id,
                SecurityFinding.is_fixed == False
            ).count()
        
            # Query fixed count
            fixed = self.db.query(SecurityFinding).filter(
                SecurityFinding.team_id == team_id,
                SecurityFinding.is_fixed == True
            ).count()
        
            # Query average patch confidence
            avg_confidence = self.db.query(func.avg(Patch.confidence_score)).filter(
                Patch.team_id == team_id
            ).scalar() or 0
        
            # Query repository count
            repo_count = self.db.query(TeamRepository).filter(
                TeamRepository.team_id == team_id,
                TeamRepository.is_active == True
            ).count()
        
            return {
                "critical_open": critical,
                "total_open": total,
                "fixed_count": fixed,
                "fix_rate": (fixed / (fixed + total) * 100) if (fixed + total) > 0 else 0,
                "avg_patch_confidence": float(avg_confidence),
                "active_repositories": repo_count,
                "timestamp": datetime.utcnow()
            }
    
        def get_severity_distribution(self, team_id: str) -> Dict:
            """Get findings distributed by severity."""
            from app.db.models import SecurityFinding, SeverityLevel
        
            distribution = {}
            for severity in SeverityLevel:
                count = self.db.query(SecurityFinding).filter(
                    SecurityFinding.team_id == team_id,
                    SecurityFinding.severity == severity,
                    SecurityFinding.is_fixed == False
                ).count()
                distribution[severity.value] = count
        
            return distribution


    # ============================================================================
    # ADVANCED FILTERING
    # ============================================================================

    class AdvancedFilter:
        """Advanced finding filters for enterprise users."""
    
        def __init__(self, db: Session):
            self.db = db
    
        def filter_findings(
            self,
            team_id: str,
            severity: Optional[List[str]] = None,
            status: Optional[List[str]] = None,
            language: Optional[List[str]] = None,
            days_old: Optional[int] = None
        ) -> list:
            """Apply multiple filters to findings."""
            from app.db.models import SecurityFinding, SeverityLevel
        
            query = self.db.query(SecurityFinding).filter(
                SecurityFinding.team_id == team_id
            )
        
            # Severity filter
            if severity:
                severity_enums = [SeverityLevel[s.upper()] for s in severity if s.upper() in SeverityLevel.__members__]
                if severity_enums:
                    query = query.filter(SecurityFinding.severity.in_(severity_enums))
        
            # Status filter
            if status:
                query = query.filter(SecurityFinding.status.in_(status))
        
            # Date filter
            if days_old:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                query = query.filter(SecurityFinding.created_at >= cutoff_date)
        
            return query.all()
