# 🔑 Gemini API Setup Guide

## Step 1: Get Your Free Gemini API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Click **"Create API key"**
3. Select your project (or create a new one)
4. Copy the generated API key

## Step 2: Add API Key to `.env` File

**File location:** `/workspaces/fix.ai/backend/.env`

Find this line:
```dotenv
GEMINI_API_KEY=ADD_YOUR_GEMINI_API_KEY_HERE
```

Replace with your actual key (example):
```dotenv
GEMINI_API_KEY=AIzaSyD_hc_example_key_12345_abc
```

## Step 3: Security - Keep It Secret! 🔐

**✅ Your `.env` file is PROTECTED:**
- Added to `.gitignore` ✓
- Won't be committed to GitHub ✓
- Only stored locally on your machine ✓

**Never:**
- ❌ Commit `.env` file to GitHub
- ❌ Share your API key publicly
- ❌ Hardcode it in source code

## Step 4: Start Using It!

Once you add the API key, your VulnSentinel app will:
- ✅ Auto-detect vulnerabilities using Semgrep
- ✅ Use Gemini AI to generate fixes automatically
- ✅ Post code review comments on GitHub PRs
- ✅ Create patches for security issues

## Available Gemini Models

- `gemini-pro` - Best for code analysis (Recommended)
- `gemini-pro-vision` - With image capabilities
- `gemini-1.5-pro` - Latest version (if available)

## Rate Limits (Free Tier)

- 60 API calls per minute
- 1,500 requests per day
- Perfect for development and testing

## API Configuration in Code

The app automatically handles Gemini:

```python
# Backend uses: app/services/remediation.py
if settings.LLM_PROVIDER == "gemini":
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Generates patches using Gemini AI
```

## Troubleshooting

### "Invalid API Key" Error
- Check if key is copied correctly (no extra spaces)
- Verify key hasn't been regenerated
- Make sure it's in `.env` file (not `.env.example`)

### Rate Limit Exceeded
- Wait a few minutes before next API call
- Increase `LLM_CONCURRENCY` in `.env` if needed

### API Not Working
1. Check `.env` has `LLM_PROVIDER=gemini`
2. Verify `GEMINI_API_KEY` is set
3. Check internet connection
4. Review logs: `docker logs vulnsentinel-backend`

## Environment Variables Reference

```dotenv
# LLM Configuration
LLM_PROVIDER=gemini          # Use "gemini" or "openai"
GEMINI_API_KEY=AIzaSy...     # Your API key
LLM_MODEL=gemini-pro         # Model to use
LLM_CONCURRENCY=3            # Parallel requests
LLM_MAX_FILE_CHARS=200000    # Max file size to process
LLM_MAX_RETRIES=2            # Retry attempts
```

---

**Setup complete! Your API key is now secure and integrated. 🎉**
