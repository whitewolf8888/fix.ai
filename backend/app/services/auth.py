"""Authentication helpers: password hashing, JWT tokens, RBAC."""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings
from app.db.auth_store import AuthStore, UserRecord
from app.dependencies import get_auth_store, get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, settings_obj: Settings) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings_obj.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**data, "exp": expire}
    return jwt.encode(to_encode, settings_obj.JWT_SECRET_KEY, algorithm=settings_obj.JWT_ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_store: AuthStore = Depends(get_auth_store),
    settings_obj: Settings = Depends(get_settings),
) -> Optional[UserRecord]:
    """Return current user from JWT token."""
    if not settings_obj.AUTH_ENABLED:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings_obj.JWT_SECRET_KEY, algorithms=[settings_obj.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await auth_store.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


def require_roles(roles: List[str]):
    """Dependency factory to enforce role-based access."""

    async def _require_roles(user: Optional[UserRecord] = Depends(get_current_user), settings_obj: Settings = Depends(get_settings)):
        if not settings_obj.AUTH_ENABLED:
            return None
        if user is None or user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _require_roles
