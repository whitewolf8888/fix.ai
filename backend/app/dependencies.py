"""FastAPI dependency injection providers."""

from app.core.config import settings, Settings
from app.db.store import get_store, BaseStore
from app.db.auth_store import AuthStore
from app.db.analytics_store import AnalyticsStore
from app.db.license_store import LicenseStore
from app.db.pilot_store import PilotStore
from app.db.settings_store import SettingsStore


# Global store instances
_store_instance = None
_auth_store_instance = None
_analytics_store_instance = None
_license_store_instance = None
_pilot_store_instance = None
_settings_store_instance = None


async def get_task_store() -> BaseStore:
    """Dependency to provide task store."""
    global _store_instance
    if _store_instance is None:
        _store_instance = await get_store(
            store_type=settings.STORE_BACKEND,
            db_path=settings.DB_PATH,
            max_memory=settings.MAX_MEMORY_TASKS,
            database_url=settings.DATABASE_URL,
        )
    return _store_instance


async def get_auth_store() -> AuthStore:
    """Dependency to provide auth store."""
    global _auth_store_instance
    if _auth_store_instance is None:
        _auth_store_instance = AuthStore(
            backend=settings.AUTH_DB_BACKEND,
            db_path=settings.DB_PATH,
            database_url=settings.DATABASE_URL,
        )
    return _auth_store_instance


async def get_analytics_store() -> AnalyticsStore:
    """Dependency to provide analytics store."""
    global _analytics_store_instance
    if _analytics_store_instance is None:
        _analytics_store_instance = AnalyticsStore(
            backend=settings.AUTH_DB_BACKEND,
            db_path=settings.DB_PATH,
            database_url=settings.DATABASE_URL,
        )
    return _analytics_store_instance


async def get_license_store() -> LicenseStore:
    """Dependency to provide license store."""
    global _license_store_instance
    if _license_store_instance is None:
        _license_store_instance = LicenseStore(
            backend=settings.AUTH_DB_BACKEND,
            db_path=settings.DB_PATH,
            database_url=settings.DATABASE_URL,
        )
    return _license_store_instance


async def get_pilot_store() -> PilotStore:
    """Dependency to provide pilot store."""
    global _pilot_store_instance
    if _pilot_store_instance is None:
        _pilot_store_instance = PilotStore(
            backend=settings.AUTH_DB_BACKEND,
            db_path=settings.DB_PATH,
            database_url=settings.DATABASE_URL,
        )
    return _pilot_store_instance


async def get_settings_store() -> SettingsStore:
    """Dependency to provide settings store."""
    global _settings_store_instance
    if _settings_store_instance is None:
        _settings_store_instance = SettingsStore(
            backend=settings.AUTH_DB_BACKEND,
            db_path=settings.DB_PATH,
            database_url=settings.DATABASE_URL,
        )
    return _settings_store_instance


def get_settings() -> Settings:
    """Dependency to provide settings."""
    return settings
