# 🚀 VulnSentinel Deployment Guide

Complete guide for deploying VulnSentinel to production environments.

## Table of Contents

- [Quick Start with Docker](#quick-start-with-docker)
- [Production Deployment](#production-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Environment Configuration](#environment-configuration)
- [SSL/TLS Setup](#ssltls-setup)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## Quick Start with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM
- 10GB+ disk space

### 1. Clone Repository
```bash
git clone https://github.com/whitewolf8888/fix.ai.git
cd fix.ai
```

### 2. Configure Environment
```bash
# Copy example environment file
cp backend/.env.example backend/.env

# Edit with your API keys
nano backend/.env
```

**Required Configuration:**
```env
# Choose LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here

# GitHub Integration
GITHUB_TOKEN=ghp_your-token-here
GITHUB_WEBHOOK_SECRET=your-random-secret-here
```

### 3. Start Services
```bash
# Development mode
docker-compose up -d

# Production mode with Nginx
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Deployment
```bash
# Check services
docker-compose ps

# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000
```

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Production Deployment

### Using Docker Compose with Nginx

1. **Setup Nginx reverse proxy:**
```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

2. **Configure SSL (Let's Encrypt):**
```bash
# Install Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Update nginx config
sudo nano nginx/nginx.conf
# Uncomment HTTPS server block and update domain
```

3. **Configure firewall:**
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Manual Installation (Without Docker)

#### Backend Setup
```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env

# Run with production settings
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Start production server
npm start
```

---

## Cloud Platforms

### Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

1. **Fork this repository**
2. **Create new Railway project**
3. **Add services:**
   - Backend service: `backend/`
   - Frontend service: `frontend/`
4. **Configure environment variables** (see Environment Configuration)
5. **Deploy** 🚀

**Railway Configuration:**

**Backend:**
```toml
# railway.toml (backend)
[build]
builder = "DOCKERFILE"
dockerfilePath = "backend/Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

**Frontend:**
```toml
# railway.toml (frontend)
[build]
builder = "DOCKERFILE"
dockerfilePath = "frontend/Dockerfile"

[deploy]
startCommand = "node server.js"
```

### Deploy to Vercel (Frontend) + Railway (Backend)

**Frontend on Vercel:**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy frontend
cd frontend
vercel --prod
```

**Backend on Railway:**
- Import backend directory
- Add environment variables
- Deploy automatically

### Deploy to AWS ECS

1. **Build and push Docker images:**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t vulnsentinel-backend ./backend
docker tag vulnsentinel-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/vulnsentinel-backend:latest

# Push
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/vulnsentinel-backend:latest
```

2. **Create ECS task definition** (see `aws-ecs-task-definition.json`)

3. **Deploy service:**
```bash
aws ecs create-service \
  --cluster vulnsentinel-cluster \
  --service-name vulnsentinel-backend \
  --task-definition vulnsentinel-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

### Deploy to DigitalOcean App Platform

1. **Create new app** from GitHub repository
2. **Configure components:**
   - **Backend:** Dockerfile: `backend/Dockerfile`
   - **Frontend:** Dockerfile: `frontend/Dockerfile`
3. **Add environment variables**
4. **Deploy**

### Deploy to Heroku

**Backend:**
```bash
cd backend
heroku create vulnsentinel-backend
heroku stack:set container
git push heroku main
```

**Frontend:**
```bash
cd frontend
heroku create vulnsentinel-frontend
heroku stack:set container
git push heroku main
```

---

## Environment Configuration

### Backend Environment Variables

```env
# App Configuration
APP_NAME=VulnSentinel
APP_VERSION=4.1.0
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Storage (sqlite or memory)
STORE_BACKEND=sqlite
DB_PATH=/data/vulnsentinel.db
DATABASE_URL=postgresql://vulnsentinel:change-me@postgres:5432/vulnsentinel

# Scanner
SEMGREP_CONFIG=auto
SCAN_TIMEOUT_SECONDS=300

# LLM Provider (openai or gemini)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx
# OR
# GEMINI_API_KEY=AIzaSyxxxxx
LLM_MODEL=gpt-4-turbo
LLM_CONCURRENCY=3

# GitHub Integration
GITHUB_TOKEN=ghp_xxxxx
GITHUB_WEBHOOK_SECRET=your-secure-random-secret
GITHUB_WEBHOOK_POST_PR_COMMENT=true

# Auth & Security
AUTH_ENABLED=true
AUTH_DB_BACKEND=postgres
JWT_SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
BOOTSTRAP_ADMIN_EMAIL=admin@yourdomain.com
BOOTSTRAP_ADMIN_PASSWORD=StrongPassword123

# Queue
QUEUE_BACKEND=redis
REDIS_URL=redis://redis:6379/0

# Billing (Stripe)
BILLING_ENABLED=true
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_starter
STRIPE_PRICE_GROWTH=price_growth
STRIPE_PRICE_ENTERPRISE=price_enterprise
STRIPE_SUCCESS_URL=https://yourdomain.com/billing/success
STRIPE_CANCEL_URL=https://yourdomain.com/billing/cancel

# License Verification
LICENSE_BOOTSTRAP_KEY=client_ABC_123
LICENSE_BOOTSTRAP_OWNER=client@company.com
LICENSE_TRACK_NEW_IPS=true

# Pilot Automation
AUTO_PILOT_ENABLED=true
AUTO_PILOT_MIN_TEAM_SIZE=5
AUTO_PILOT_ALLOWED_DOMAINS=company.com,example.com

# Pilot Email
PILOT_EMAIL_ENABLED=true
PILOT_EMAIL_FROM=pilot@yourdomain.com
PILOT_REMINDER_SUBJECT=VulnSentinel Pilot Reminder
PILOT_REMINDER_DAYS=3,7,14
PILOT_REMINDER_INTERVAL_HOURS=24

# Alerts
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENTS=alerts@yourdomain.com
SMTP_HOST=smtp.yourdomain.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=strong-password
SMTP_FROM=alerts@yourdomain.com
SMTP_USE_TLS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

# Auto-remediation
REMEDIATE_SEVERITIES=ERROR,WARNING,HIGH,MEDIUM
```

### Frontend Environment Variables

```env
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
PORT=3000
```

---

## SSL/TLS Setup

### Let's Encrypt (Certbot)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Cloudflare SSL

1. Add your domain to Cloudflare
2. Update DNS to point to your server
3. Enable "Full (strict)" SSL mode
4. Use origin certificates for backend

### Custom SSL Certificate

```bash
# Generate self-signed certificate (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Backend health
curl https://yourdomain.com/health

# Expected response:
{
  "status": "healthy",
  "version": "4.1.0",
  "store_backend": "sqlite",
  "llm_configured": true,
  "semgrep_available": true
}
```

### Logging

**Docker Logs:**
```bash
# View backend logs
docker-compose logs -f backend

# View frontend logs
docker-compose logs -f frontend

# View all logs
docker-compose logs -f
```

**Log Files:**
- Backend: `/var/log/nginx/backend_access.log`
- Frontend: `/var/log/nginx/frontend_access.log`
- Nginx: `/var/log/nginx/error.log`

### Database Backup

```bash
# Backup SQLite database
docker-compose exec backend cp /data/vulnsentinel.db /tmp/backup.db
docker cp vulnsentinel-backend:/tmp/backup.db ./backup-$(date +%Y%m%d).db

# Restore backup
docker cp ./backup-20260224.db vulnsentinel-backend:/data/vulnsentinel.db
docker-compose restart backend
```

### Updates & Maintenance

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Clean old images
docker image prune -a
```

### Performance Tuning

**Backend Workers:**
```dockerfile
# In Dockerfile, adjust workers based on CPU cores
CMD ["uvicorn", "app.main:app", "--workers", "4", ...]
# Rule of thumb: (2 × CPU cores) + 1
```

**Database Optimization:**
```python
# Use connection pooling for high load
STORE_BACKEND=sqlite
# Or use PostgreSQL for production
```

---

## Troubleshooting

### Backend Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs backend

# Verify environment
docker-compose exec backend env | grep API_KEY
```

**Database locked:**
```bash
# SQLite timeout - restart service
docker-compose restart backend
```

### Frontend Issues

**Build failures:**
```bash
# Clear cache
docker-compose exec frontend rm -rf .next node_modules
docker-compose exec frontend npm install
docker-compose restart frontend
```

**API connection errors:**
```bash
# Check NEXT_PUBLIC_API_URL
# Ensure backend is accessible
curl http://backend:8000/health
```

### Network Issues

**Services can't communicate:**
```bash
# Check Docker network
docker network inspect fix_vulnsentinel-network

# Restart networking
docker-compose down
docker-compose up -d
```

---

## Security Checklist

- [ ] Change default `GITHUB_WEBHOOK_SECRET`
- [ ] Use strong API keys
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up rate limiting (included)
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Use secrets management (Vault, AWS Secrets Manager)
- [ ] Enable 2FA on GitHub
- [ ] Restrict CORS origins in production

---

## Support

For issues and questions:
- 📚 [Documentation](https://github.com/whitewolf8888/fix.ai)
- 🐛 [Issues](https://github.com/whitewolf8888/fix.ai/issues)
- 💬 [Discussions](https://github.com/whitewolf8888/fix.ai/discussions)

---

**Made with ❤️ by VulnSentinel Team**
