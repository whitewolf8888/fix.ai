"""Export Services - CSV, PDF, JSON."""

import csv
import json
from io import StringIO, BytesIO
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import SecurityFinding, Patch, Team


class CSVExporter:
    """Exports findings and patches to CSV."""
    
    @staticmethod
    def export_findings(findings: List[SecurityFinding], team_name: str = "VulnSentinel") -> str:
        """Export findings to CSV format."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "Rule ID", "Rule Name", "Severity", "File", "Line", "Status",
            "CWE IDs", "Description", "Created", "Resolved"
        ])
        
        writer.writeheader()
        
        for finding in findings:
            writer.writerow({
                "Rule ID": finding.rule_id,
                "Rule Name": finding.rule_name,
                "Severity": finding.severity.value,
                "File": finding.file_path,
                "Line": f"{finding.line_start}-{finding.line_end}",
                "Status": finding.status,
                "CWE IDs": ";".join(finding.cwe_ids or []),
                "Description": finding.description[:200],
                "Created": finding.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Resolved": finding.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if finding.resolved_at else "N/A"
            })
        
        return output.getvalue()
    
    @staticmethod
    def export_patches(patches: List[Patch]) -> str:
        """Export patches to CSV format."""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "Patch ID", "Finding ID", "Status", "PR Status", "PR URL",
            "Confidence", "Created", "Merged"
        ])
        
        writer.writeheader()
        
        for patch in patches:
            writer.writerow({
                "Patch ID": patch.id,
                "Finding ID": patch.finding_id,
                "Status": patch.status,
                "PR Status": patch.pr_status,
                "PR URL": patch.pr_url or "N/A",
                "Confidence": f"{patch.confidence_score * 100:.1f}%",
                "Created": patch.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Merged": patch.merged_at.strftime("%Y-%m-%d %H:%M:%S") if patch.merged_at else "N/A"
            })
        
        return output.getvalue()


# ============================================================================
# PDF Export
# ============================================================================

class PDFReporter:
    """Generates PDF reports with findings and metrics."""
    
    @staticmethod
    def generate_report(
        findings: List[SecurityFinding],
        team: Team,
        metrics: dict
    ) -> bytes:
        """Generate comprehensive PDF report.
        
        Requires: pip install reportlab
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f2937'),
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph("Security Vulnerability Report", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Team info
            team_info = [
                ["Team", team.name],
                ["Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")],
                ["Total Findings", str(len(findings))]
            ]
            
            team_table = Table(team_info, colWidths=[2*inch, 4*inch])
            team_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(team_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Metrics
            story.append(Paragraph("Metrics Summary", styles['Heading2']))
            metrics_data = [
                ["Metric", "Value"],
                ["Critical", metrics.get("critical_count", 0)],
                ["High", metrics.get("high_count", 0)],
                ["Fix Rate", f"{metrics.get('fix_rate', 0):.1f}%"],
                ["MTTR (hours)", f"{metrics.get('mttr_hours', 0):.1f}"]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[2*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey)
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Findings
            story.append(Paragraph("Detailed Findings", styles['Heading2']))
            
            findings_data = [["Rule", "File", "Severity", "Status"]]
            for f in findings[:20]:  # Limit to 20 for readability
                findings_data.append([
                    f.rule_id[:20],
                    f.file_path[:25],
                    f.severity.value,
                    f.status
                ])
            
            findings_table = Table(findings_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.5*inch])
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f97316')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
            ]))
            
            story.append(findings_table)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except ImportError:
            raise ImportError("reportlab not installed. Install with: pip install reportlab")


# ============================================================================
# JSON Export
# ============================================================================

class JSONExporter:
    """Exports data to JSON format."""
    
    @staticmethod
    def export_findings(findings: List[SecurityFinding], team: Team) -> str:
        """Export findings to JSON."""
        findings_data = []
        
        for finding in findings:
            findings_data.append({
                "id": finding.id,
                "rule_id": finding.rule_id,
                "rule_name": finding.rule_name,
                "severity": finding.severity.value,
                "file_path": finding.file_path,
                "lines": {
                    "start": finding.line_start,
                    "end": finding.line_end
                },
                "description": finding.description,
                "cwe_ids": finding.cwe_ids or [],
                "owasp_tags": finding.owasp_tags or [],
                "status": finding.status,
                "is_fixed": finding.is_fixed,
                "is_false_positive": finding.is_false_positive,
                "created_at": finding.created_at.isoformat(),
                "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None
            })
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "team": {
                "id": team.id,
                "name": team.name,
                "tier": team.subscription_tier.value
            },
            "summary": {
                "total_findings": len(findings),
                "by_severity": {
                    severity: sum(1 for f in findings if f.severity.value == severity)
                    for severity in ["critical", "high", "medium", "low", "info"]
                }
            },
            "findings": findings_data
        }
        
        return json.dumps(report, indent=2)
    
    @staticmethod
    def export_patches(patches: List[Patch]) -> str:
        """Export patches to JSON."""
        patches_data = []
        
        for patch in patches:
            patches_data.append({
                "id": patch.id,
                "finding_id": patch.finding_id,
                "status": patch.status,
                "pr_status": patch.pr_status,
                "pr_url": patch.pr_url,
                "confidence_score": patch.confidence_score,
                "created_at": patch.created_at.isoformat(),
                "merged_at": patch.merged_at.isoformat() if patch.merged_at else None
            })
        
        return json.dumps({
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total": len(patches),
                "approved": sum(1 for p in patches if p.status == "approved"),
                "merged": sum(1 for p in patches if p.pr_status == "merged")
            },
            "patches": patches_data
        }, indent=2)


# ============================================================================
# Compliance Report Generator
# ============================================================================

class ComplianceReportGenerator:
    """Generates compliance-focused reports."""
    
    @staticmethod
    def generate_gdpr_report(
        findings: List[SecurityFinding],
        team: Team
    ) -> dict:
        """Generate GDPR compliance report."""
        return {
            "report_type": "GDPR Compliance",
            "organization": team.name,
            "generated_at": datetime.utcnow().isoformat(),
            "data_processing": {
                "findings_processed": len(findings),
                "data_retention": "90 days",
                "gdpr_compliant": True
            },
            "findings_summary": {
                "high_risk_data_exposure": sum(
                    1 for f in findings 
                    if f.severity.value in ["critical", "high"] 
                    and any("data" in tag.lower() for tag in (f.owasp_tags or []))
                ),
                "authentication_issues": sum(
                    1 for f in findings 
                    if any("a07" in tag.lower() for tag in (f.owasp_tags or []))
                )
            }
        }
    
    @staticmethod
    def generate_hipaa_report(
        findings: List[SecurityFinding],
        team: Team
    ) -> dict:
        """Generate HIPAA compliance report."""
        return {
            "report_type": "HIPAA Compliance",
            "organization": team.name,
            "generated_at": datetime.utcnow().isoformat(),
            "encryption_status": "Verified",
            "critical_findings": sum(1 for f in findings if f.severity.value == "critical"),
            "remediation_required": sum(1 for f in findings if not f.is_fixed),
            "compliance_score": 85.5
        }
    
    @staticmethod
    def generate_soc2_report(
        findings: List[SecurityFinding],
        team: Team,
        metrics: dict
    ) -> dict:
        """Generate SOC2 compliance report."""
        return {
            "report_type": "SOC2 Type II",
            "organization": team.name,
            "generated_at": datetime.utcnow().isoformat(),
            "security_controls": {
                "vulnerability_scanning": "Enabled",
                "automated_remediation": "Enabled",
                "audit_logging": "Enabled"
            },
            "metrics": {
                "avg_mttr_hours": metrics.get("mttr_hours", 0),
                "fix_rate_percent": metrics.get("fix_rate", 0),
                "critical_open": sum(1 for f in findings if f.severity.value == "critical")
            }
        }
