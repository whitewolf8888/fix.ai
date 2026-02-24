"""GitHub PR commenting service."""

import asyncio
from typing import Optional

try:
    from github import Github, GithubException
    from github.GithubException import UnknownObjectException
except ImportError:
    Github = None
    GithubException = None
    UnknownObjectException = None

from app.services.orchestrator import ReviewResult, PatchResult
from app.core.config import Settings
from app.core.logging import logger


class GitHubBotError(Exception):
    """GitHub bot operation error."""
    pass


async def post_github_pr_review(
    repo_name: str,
    pr_number: int,
    review_result: ReviewResult,
    settings: Optional[Settings] = None,
) -> None:
    """
    Post security review as comments on a GitHub PR.
    
    Args:
        repo_name: GitHub repo: owner/repo
        pr_number: Pull request number
        review_result: ReviewResult with findings and patches
        settings: App settings
    """
    
    if settings is None:
        from app.core.config import settings as default_settings
        settings = default_settings
    
    if not settings.GITHUB_TOKEN:
        logger.warning("[GitHubBot] GITHUB_TOKEN not set; skipping PR comment")
        return
    
    loop = asyncio.get_event_loop()
    
    try:
        await loop.run_in_executor(
            None,
            _post_review_sync,
            repo_name,
            pr_number,
            review_result,
            settings.GITHUB_TOKEN,
        )
    except Exception as e:
        logger.error(f"[GitHubBot] Failed to post review: {str(e)}")


def _post_review_sync(
    repo_name: str,
    pr_number: int,
    review_result: ReviewResult,
    github_token: str,
) -> None:
    """Synchronous GitHub PR posting."""
    
    if not Github:
        raise GitHubBotError("PyGithub not installed")
    
    try:
        # Authenticate
        gh = Github(github_token)
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        logger.info(f"[GitHubBot] Posting review to {repo_name} PR #{pr_number}")
        
        # Post summary
        summary_comment = _build_summary_comment(review_result)
        pr.create_issue_comment(summary_comment)
        logger.info(f"[GitHubBot] Posted summary comment")
        
        # Post individual findings (only if findings exist)
        if review_result.all_findings:
            findings_by_severity = sorted(
                review_result.all_findings,
                key=lambda f: _severity_rank(f.severity),
            )
            
            for i, finding in enumerate(findings_by_severity[:20]):  # Max 20 individual
                finding_comment = _build_finding_comment(
                    finding,
                    i + 1,
                    len(findings_by_severity),
                    review_result.patch_results,
                )
                pr.create_issue_comment(finding_comment)
                logger.info(f"[GitHubBot] Posted finding #{i + 1}/{len(findings_by_severity)}")
        
    except UnknownObjectException:
        raise GitHubBotError(f"Repository {repo_name} or PR #{pr_number} not found")
    except Exception as e:
        raise GitHubBotError(f"GitHub API error: {str(e)}")


def _build_summary_comment(review_result: ReviewResult) -> str:
    """Build the summary comment for the PR."""
    
    if review_result.error:
        return f"""## 🔴 Security Review Failed

An error occurred during the security scan:

```
{review_result.error}
```

Please check the server logs for details.
"""
    
    if not review_result.all_findings:
        return """## ✅ Security Review Passed

No vulnerabilities detected in this pull request! Great work maintaining secure code. 🎉
"""
    
    high_count = sum(1 for f in review_result.all_findings if f.severity in ("ERROR", "HIGH"))
    medium_count = sum(1 for f in review_result.all_findings if f.severity == "WARNING")
    low_count = len(review_result.all_findings) - high_count - medium_count
    
    summary = f"""## 🔍 Security Audit Results

Found **{len(review_result.all_findings)}** vulnerabilities:

| Severity | Count |
|----------|-------|
| 🔴 ERROR/HIGH | {high_count} |
| 🟠 MEDIUM/WARNING | {medium_count} |
| 🟡 LOW | {low_count} |

**AI Patches Available:** {len([p for p in review_result.patch_results if p.patched_content])}

---

Scroll down to see detailed findings and AI-generated patches.
"""
    
    return summary


def _build_finding_comment(
    finding,
    index: int,
    total: int,
    patch_results: list,
) -> str:
    """Build comment for a single finding."""
    
    emoji = {"ERROR": "🔴", "HIGH": "🔴", "WARNING": "🟠", "MEDIA": "🟡", "INFO": "⚪"}.get(
        finding.severity,
        "⚪",
    )
    
    # Find patch for this finding
    patch = next((p for p in patch_results if p.finding.rule_id == finding.rule_id), None)
    patch_status = "✅ AI Patch Available" if patch and patch.patched_content else "❌ No patch"
    
    comment = f"""
### {emoji} Finding {index}/{total}: `{finding.rule_id}`

**Severity:** {emoji} {finding.severity} | **Confidence:** {finding.confidence}

**File:** `{finding.file_path}` (lines {finding.line_start}–{finding.line_end})

**Description:** {finding.description}

"""
    
    if finding.cwe_ids:
        comment += f"**CWE:** {', '.join(finding.cwe_ids)}\n\n"
    
    if finding.owasp_tags:
        comment += f"**OWASP:** {', '.join(finding.owasp_tags)}\n\n"
    
    # Vulnerable snippet
    comment += f"""<details>
<summary>🔸 Vulnerable Code</summary>

```python
{finding.code_snippet}
```

</details>

"""
    
    # Patch (if available)
    if patch and patch.patched_content:
        extension = _get_extension(finding.file_path)
        comment += f"""<details open>
<summary>💡 AI-Generated Fix {patch_status}</summary>

```{extension}
{patch.patched_content[:8000]}
```

> **Our AI Security Agent suggests the following fix.** Please review carefully before merging.

1. Copy the patched code above
2. Replace the vulnerable code in `{finding.file_path}`
3. Test thoroughly in your local environment
4. Commit and push to this PR

</details>

---

"""
    else:
        comment += f"\n**Patch Status:** {patch_status}\n\n---\n\n"
    
    return comment


def _build_batch_comment(patch_results: list[PatchResult]) -> str:
    """Build a batch comment for remaining findings."""
    
    comment = "### 📦 Additional Findings (Batch)\n\n"
    
    for i, result in enumerate(patch_results, 1):
        finding = result.finding
        comment += f"**{i}. {finding.rule_id}** ({finding.severity}) in `{finding.file_path}`\n"
        if result.patched_content:
            comment += f"   ✅ Patch available\n"
        elif result.error:
            comment += f"   ❌ {result.error}\n"
        comment += "\n"
    
    return comment


def _severity_rank(severity: str) -> int:
    """Rank severity for sorting (lower = more severe)."""
    ranks = {"ERROR": 0, "HIGH": 1, "WARNING": 2, "MEDIA": 3, "INFO": 4}
    return ranks.get(severity.upper(), 99)


def _get_extension(file_path: str) -> str:
    """Get file extension for code highlighting."""
    extensions = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
    }
    
    for ext, lang in extensions.items():
        if file_path.endswith(ext):
            return lang
    
    return "text"
