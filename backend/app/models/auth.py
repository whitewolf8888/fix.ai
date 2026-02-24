"""Authentication and user models."""

from datetime import datetime
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Register a new user."""

    email: str
    password: str = Field(min_length=8)
    role: str = Field(default="viewer")


class LoginRequest(BaseModel):
    """User login request."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    """Public user profile."""

    user_id: str
    email: str
    role: str
    created_at: datetime
