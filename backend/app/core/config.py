"""Configuration for VulnSentinel backend."""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    APP_NAME: str = "VulnSentinel"
    APP_VERSION: str = "4.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Storage
    STORE_BACKEND: Literal["memory", "sqlite", "postgres"] = "sqlite"
    DB_PATH: str = "vulnsentinel.db"
    DATABASE_URL: str = ""
    MAX_MEMORY_TASKS: int = 500

    # Scanner
    SEMGREP_CONFIG: str = "auto"
    SCAN_TIMEOUT_SECONDS: int = 300
    CLONE_DEPTH: int = 1

    # LLM
    LLM_PROVIDER: Literal["openai", "gemini"] = "openai"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4-turbo"
    LLM_CONCURRENCY: int = 3
    LLM_MAX_FILE_CHARS: int = 200_000
    LLM_MAX_RETRIES: int = 2

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = "local-dev-secret-change-me-in-production"
    GITHUB_WEBHOOK_MAX_CONCURRENCY: int = 3
    GITHUB_WEBHOOK_POST_PR_COMMENT: bool = True

    # Auth & Security
    AUTH_ENABLED: bool = False
    AUTH_DB_BACKEND: Literal["sqlite", "postgres"] = "sqlite"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    # Queue
    QUEUE_BACKEND: Literal["local", "redis"] = "local"
    REDIS_URL: str = ""

    # Billing (Stripe)
    BILLING_ENABLED: bool = False
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    STRIPE_SUCCESS_URL: str = ""
    STRIPE_CANCEL_URL: str = ""

    # License Verification
    LICENSE_BOOTSTRAP_KEY: str = ""
    LICENSE_BOOTSTRAP_OWNER: str = ""
    LICENSE_TRACK_NEW_IPS: bool = True

    # Pilot Automation
    AUTO_PILOT_ENABLED: bool = False
    AUTO_PILOT_MIN_TEAM_SIZE: int = 0
    AUTO_PILOT_ALLOWED_DOMAINS: str = ""

    # Pilot Email
    PILOT_EMAIL_ENABLED: bool = False
    PILOT_EMAIL_FROM: str = ""
    PILOT_REMINDER_SUBJECT: str = ""
    PILOT_REMINDER_DAYS: str = "3,7,14"
    PILOT_REMINDER_INTERVAL_HOURS: int = 24

    # Alerts
    ALERT_EMAIL_ENABLED: bool = False
    ALERT_EMAIL_RECIPIENTS: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    SLACK_WEBHOOK_URL: str = ""

    # Auto-remediation
    REMEDIATE_SEVERITIES: str = "ERROR,WARNING,HIGH,MEDIUM"

    class Config:
        """Pydantic settings config."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()
