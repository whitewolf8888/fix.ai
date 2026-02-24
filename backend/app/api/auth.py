"""Authentication endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings
from app.core.logging import logger
from app.db.auth_store import AuthStore, UserRecord
from app.dependencies import get_auth_store, get_settings
from app.models.auth import RegisterRequest, LoginRequest, TokenResponse, UserPublic
from app.services.auth import get_password_hash, verify_password, create_access_token, get_current_user, require_roles


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    auth_store: AuthStore = Depends(get_auth_store),
    settings: Settings = Depends(get_settings),
) -> UserPublic:
    """Register a new user."""
    existing = await auth_store.get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = UserRecord(
        user_id=str(uuid.uuid4()),
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role,
        created_at=datetime.utcnow(),
    )
    await auth_store.create_user(user)

    logger.info(f"[Auth] Registered user {request.email}")

    return UserPublic(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: LoginRequest,
    auth_store: AuthStore = Depends(get_auth_store),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Authenticate a user and return a JWT token."""
    user = await auth_store.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": user.user_id, "role": user.role}, settings)

    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)) -> UserPublic:
    """Return current user profile."""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return UserPublic(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    auth_store: AuthStore = Depends(get_auth_store),
    _user=Depends(require_roles(["admin"]))
) -> list[UserPublic]:
    """List users (admin only)."""
    users = await auth_store.list_users()
    return [
        UserPublic(
            user_id=u.user_id,
            email=u.email,
            role=u.role,
            created_at=u.created_at,
        )
        for u in users
    ]
