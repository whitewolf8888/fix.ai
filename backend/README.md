# VulnSentinel Backend

Enterprise FastAPI backend for automated code security scanning and AI-powered remediation.

## Quick Start

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install semgrep

# 2. Configure
cp .env.example .env
# Fill in your LLM keys + GitHub token

# 3. Run
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` to verify.

Docs: `http://localhost:8000/docs` (Swagger UI)

## Architecture

- **Async**: FastAPI with async/await for non-blocking operations
- **Background Tasks**: Git clone, Semgrep scan, LLM calls run in thread pools
- **Storage**: SQLite persistence with in-memory fallback
- **LLM**: OpenAI or Google Gemini support
- **GitHub**: Webhook + PR automation

## API Endpoints

- `POST /api/scan` - Start security scan (returns task_id)
- `GET /api/status/{task_id}` - Poll scan progress
- `POST /api/remediate` - Generate AI patch for a finding
- `POST /api/remediate/bulk` - Batch remediate findings
- `POST /api/fix` - Create GitHub PR with patch
- `POST /api/webhook/github` - GitHub webhook handler
- `GET /health` - Health check

## Environment Variables

See `.env.example` for all configuration options.

Key ones:
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Google Gemini API key
- `GITHUB_TOKEN` - GitHub personal access token
- `GITHUB_WEBHOOK_SECRET` - Webhook HMAC secret
- `STORE_BACKEND` - "sqlite" or "memory"
- `SEMGREP_CONFIG` - "auto" or custom ruleset
