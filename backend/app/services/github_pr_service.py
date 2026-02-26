"""GitHub Auto-PR Creation Service."""

from typing import Optional, List
from github import Github, GithubException
from datetime import datetime
import base64
import uuid

from app.db.models import Patch, SecurityFinding, TeamRepository
from sqlalchemy.orm import Session


class GitHubPRService:
    """Creates automatic pull requests with security fixes."""
    
    def __init__(self, github_token: str):
        """Initialize with GitHub token."""
        self.client = Github(github_token)
        self.github_token = github_token
    
    def create_fix_pr(
        self,
        db: Session,
        finding: SecurityFinding,
        patch: Patch,
        repository: TeamRepository
    ) -> Optional[dict]:
        """Create a pull request with the security fix.
        
        Args:
            db: Database session
            finding: Security finding
            patch: Generated patch
            repository: Target repository
            
        Returns:
            PR details or None if failed
        """
        try:
            # Parse repository URL
            repo_url = repository.repo_url
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]
            
            # Extract owner/repo from URL
            if 'github.com' not in repo_url:
                return None
            
            repo_path = repo_url.split('github.com/')[-1]
            repo = self.client.get_repo(repo_path)
            
            # Prepare branch name
            branch_name = f"fix/security-{finding.rule_id.replace('/', '-')}-{str(uuid.uuid4())[:8]}"
            
            # Get the base branch
            base_branch = repository.default_branch or "main"
            
            try:
                base = repo.get_branch(base_branch)
            except GithubException:
                # Fallback to master if main doesn't exist
                base = repo.get_branch("master")
                base_branch = "master"
            
            # Create a new branch from base
            new_branch = repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base.commit.sha
            )
            
            # Get the file to patch
            file_path = finding.file_path
            
            try:
                file_content = repo.get_contents(file_path, ref=branch_name)
                current_content = file_content.decoded_content.decode('utf-8')
            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist, skip
                    return None
                raise
            
            # Apply the patch
            updated_content = patch.patched_content
            
            # Commit the change
            repo.update_file(
                path=file_path,
                message=f"🔒 Security Fix: {finding.rule_name}\n\n"
                        f"Rule: {finding.rule_id}\n"
                        f"Severity: {finding.severity.value}\n"
                        f"File: {file_path}:{finding.line_start}",
                content=updated_content,
                sha=file_content.sha,
                branch=branch_name
            )
            
            # Create PR
            pr_body = self._generate_pr_body(finding, patch)
            
            pull_request = repo.create_pull(
                title=f"🔒 Security Fix: {finding.rule_name}",
                body=pr_body,
                head=branch_name,
                base=base_branch
            )
            
            # Update patch record
            patch.pr_url = pull_request.html_url
            patch.pr_status = "open"
            patch.status = "approved"
            db.commit()
            
            return {
                "pr_number": pull_request.number,
                "pr_url": pull_request.html_url,
                "branch": branch_name,
                "status": "open"
            }
            
        except Exception as e:
            print(f"❌ Failed to create PR: {str(e)}")
            return None
    
    def _generate_pr_body(self, finding: SecurityFinding, patch: Patch) -> str:
        """Generate PR description."""
        cwe_text = ""
        if finding.cwe_ids:
            cwe_links = [f"https://cwe.mitre.org/data/definitions/{cwe.split('-')[1]}.html" 
                         for cwe in finding.cwe_ids]
            cwe_text = f"\n**CWE References:**\n" + "\n".join(f"- {link}" for link in cwe_links)
        
        owasp_text = ""
        if finding.owasp_tags:
            owasp_text = f"\n**OWASP Tags:** {', '.join(finding.owasp_tags)}"
        
        body = f"""## 🔒 Security Vulnerability Fix

**Vulnerability Details:**
- **Rule:** {finding.rule_id}
- **Name:** {finding.rule_name}
- **Severity:** ⚠️ **{finding.severity.value.upper()}**
- **File:** `{finding.file_path}`
- **Lines:** {finding.line_start}-{finding.line_end}

**Description:**
{finding.description}

{cwe_text}

{owasp_text}

---

## 🔧 Fix Applied

**Confidence Score:** {patch.confidence_score * 100:.1f}%

### Code Change
```diff
{self._generate_diff(patch)}
```

**Code Snippet (Original):**
```
{finding.code_snippet}
```

---

## ✅ Next Steps

1. **Review** this pull request for correctness
2. **Test** the changes in your environment
3. **Approve and Merge** when satisfied

Created by [VulnSentinel Auto-Fix](https://github.com/whitewolf8888/fix.ai)
"""
        return body
    
    @staticmethod
    def _generate_diff(patch: Patch) -> str:
        """Generate a diff between original and patched content."""
        import difflib
        
        original_lines = patch.original_content.splitlines(keepends=True)
        patched_lines = patch.patched_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile="original",
            tofile="fixed",
            lineterm=""
        )
        
        return "".join(diff)[:500]  # Limit to 500 chars for readability
    
    def merge_pr(self, repo_path: str, pr_number: int) -> bool:
        """Merge a pull request."""
        try:
            repo = self.client.get_repo(repo_path)
            pr = repo.get_pull(pr_number)
            
            if pr.mergeable:
                pr.merge(
                    commit_title=f"Merge security fix PR #{pr_number}",
                    merge_method="squash"
                )
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to merge PR: {str(e)}")
            return False
    
    def close_pr(self, repo_path: str, pr_number: int, reason: str = "") -> bool:
        """Close a pull request."""
        try:
            repo = self.client.get_repo(repo_path)
            pr = repo.get_pull(pr_number)
            
            comment = f"Closed: {reason}" if reason else "Closed by VulnSentinel"
            pr.create_issue_comment(comment)
            pr.edit(state="closed")
            
            return True
        except Exception as e:
            print(f"❌ Failed to close PR: {str(e)}")
            return False
    
    def add_pr_comment(
        self,
        repo_path: str,
        pr_number: int,
        comment: str
    ) -> bool:
        """Add a comment to a pull request."""
        try:
            repo = self.client.get_repo(repo_path)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            return True
        except Exception as e:
            print(f"❌ Failed to add comment: {str(e)}")
            return False
    
    def get_pr_status(self, repo_path: str, pr_number: int) -> Optional[dict]:
        """Get PR status."""
        try:
            repo = self.client.get_repo(repo_path)
            pr = repo.get_pull(pr_number)
            
            return {
                "number": pr.number,
                "state": pr.state,
                "title": pr.title,
                "url": pr.html_url,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "mergeable": pr.mergeable,
                "merged": pr.merged,
                "merged_at": pr.merged_at
            }
        except Exception as e:
            print(f"❌ Failed to get PR status: {str(e)}")
            return None


class AutoPROrchestrator:
    """Orchestrates automatic PR creation for multiple findings."""
    
    def __init__(self, github_token: str, db: Session):
        self.pr_service = GitHubPRService(github_token)
        self.db = db
    
    def create_batch_prs(
        self,
        findings: List[SecurityFinding],
        patches: List[Patch],
        repository: TeamRepository,
        auto_approve: bool = False
    ) -> dict:
        """Create multiple PRs for findings.
        
        Args:
            findings: List of security findings
            patches: List of corresponding patches
            repository: Target repository
            auto_approve: Whether to auto-approve PRs (if criteria met)
            
        Returns:
            Summary of PR creation results
        """
        results = {
            "total": len(findings),
            "created": 0,
            "failed": 0,
            "prs": []
        }
        
        for finding, patch in zip(findings, patches):
            if patch.status == "pending" and patch.confidence_score > 0.7:
                pr_result = self.pr_service.create_fix_pr(
                    self.db,
                    finding,
                    patch,
                    repository
                )
                
                if pr_result:
                    results["created"] += 1
                    results["prs"].append(pr_result)
                else:
                    results["failed"] += 1
        
        return results
