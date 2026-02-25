"""AI-powered code remediation using LLMs."""

import asyncio
import re
from typing import Optional

try:
    import openai
except ImportError:
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.models.task import Finding
from app.core.config import Settings
from app.core.logging import logger


class RemediationError(Exception):
    """Remediation pipeline error."""
    pass


async def generate_enterprise_patch(
    file_path: str,
    finding: Finding,
    file_content: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> str:
    """
    Generate AI remediation patch for a vulnerable file.
    
    Args:
        file_path: Path to vulnerable file
        finding: Security finding from Semgrep
        file_content: Full source code (read from disk if None)
        settings: App settings
    
    Returns:
        Patched code content
    
    Raises:
        RemediationError: On LLM errors
    """
    
    if settings is None:
        from app.core.config import settings as default_settings
        settings = default_settings
    
    # Read file if not provided
    if file_content is None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except Exception as e:
            raise RemediationError(f"Cannot read {file_path}: {str(e)}")
    
    # Enforce token budget
    file_content = _truncate_by_chars(file_content, settings.LLM_MAX_FILE_CHARS)
    
    # Build prompt
    system_prompt = (
        "You are an elite DevSecOps AI. You are provided with the full source code of a file "
        "and a Semgrep vulnerability report. Fix the vulnerability while maintaining the exact logic, "
        "imports, and syntax context of the surrounding code. Return ONLY the fully patched, "
        "production-ready code. No markdown formatting, no explanations."
    )
    
    user_message = _build_user_message(file_path, finding, file_content)
    
    # Call LLM with retry logic
    patched_code = await _call_llm_with_retry(
        system_prompt,
        user_message,
        settings,
    )
    
    # Post-process
    patched_code = _strip_markdown_fences(patched_code)
    
    return patched_code


def _truncate_by_chars(content: str, max_chars: int) -> str:
    """Truncate file to max chars, preserving head."""
    
    if len(content) <= max_chars:
        return content
    
    # Keep first 90%, truncate end
    keep_chars = int(max_chars * 0.9)
    truncated = content[:keep_chars]
    
    # Add marker
    marker = "\n\n# VULNSENTINEL: file truncated - see full file in logs\n"
    return truncated + marker


def _build_user_message(file_path: str, finding: Finding, content: str) -> str:
    """Build structured user message for LLM."""
    
    return f"""
=== SEMGREP VULNERABILITY REPORT ===
Rule ID: {finding.rule_id}
Severity: {finding.severity}
File: {file_path}
Lines: {finding.line_start}-{finding.line_end}
Description: {finding.description}
CWE IDs: {', '.join(finding.cwe_ids) if finding.cwe_ids else 'N/A'}
OWASP: {', '.join(finding.owasp_tags) if finding.owasp_tags else 'N/A'}

Vulnerable Code (around line {finding.line_start}):
{finding.code_snippet}

=== FULL SOURCE CODE ===
{content}

=== YOUR TASK ===
Fix the vulnerability described above. Return the complete patched file. No markdown.
"""


async def _call_llm_with_retry(
    system_prompt: str,
    user_message: str,
    settings: Settings,
    retries: int = 0,
) -> str:
    """Call LLM with exponential backoff retry."""
    
    if not settings.LLM_PROVIDER or not (settings.OPENAI_API_KEY or settings.GEMINI_API_KEY):
        raise RemediationError("LLM not configured")
    
    try:
        loop = asyncio.get_event_loop()
        
        if settings.LLM_PROVIDER == "openai":
            if not openai:
                raise RemediationError("openai SDK not installed")
            
            patched = await loop.run_in_executor(
                None,
                _call_openai,
                system_prompt,
                user_message,
                settings,
            )
        elif settings.LLM_PROVIDER == "gemini":
            if not genai:
                raise RemediationError("google-generativeai SDK not installed")
            
            patched = await loop.run_in_executor(
                None,
                _call_gemini,
                system_prompt,
                user_message,
                settings,
            )
        else:
            raise RemediationError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
        
        return patched
        
    except Exception as e:
        if retries < settings.LLM_MAX_RETRIES and "rate" in str(e).lower():
            backoff = 2 ** (retries + 1)
            logger.warning(f"[Remediation] Retry {retries + 1} after {backoff}s: {str(e)}")
            await asyncio.sleep(backoff)
            return await _call_llm_with_retry(system_prompt, user_message, settings, retries + 1)
        
        raise RemediationError(f"LLM error: {str(e)}")


def _call_openai(system_prompt: str, user_message: str, settings: Settings) -> str:
    """Synchronous OpenAI call."""
    
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    
    return response.choices[0].message.content


def _call_gemini(system_prompt: str, user_message: str, settings: Settings) -> str:
    """Synchronous Google Gemini call."""
    
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        system_instruction=system_prompt,
        generation_config={"temperature": 0.0},
    )
    
    response = model.generate_content(user_message)
    return response.text


def _strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences if present."""
    
    # If entire response is wrapped in ```…```
    if content.startswith("```") and content.rstrip().endswith("```"):
        # Try to extract the inner content
        lines = content.split("\n")
        
        # Remove opening fence (potentially with language: ```python)
        if len(lines) > 1 and lines[0].startswith("```"):
            lines = lines[1:]
        
        # Remove closing fence
        if len(lines) > 0 and lines[-1].strip() == "```":
            lines = lines[:-1]
        
        content = "\n".join(lines)
    
    return content.strip()
