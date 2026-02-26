"""Team Management and Role-Based Access Control (RBAC)."""

import uuid
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets

from app.db.models import User, Team, UserRole, SubscriptionTier, APIKey
from app.core.config import settings

# ============================================================================
# Team Management
# ============================================================================

class TeamManager:
    """Manages team creation and operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_team(self, name: str, description: str = "") -> Team:
        """Create a new team."""
        team = Team(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            subscription_tier=SubscriptionTier.FREE,
            max_repos=10,
            max_team_members=5
        )
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        return self.db.query(Team).filter(Team.id == team_id).first()
    
    def get_team_by_name(self, name: str) -> Optional[Team]:
        """Get team by name."""
        return self.db.query(Team).filter(Team.name == name).first()
    
    def upgrade_subscription(self, team_id: str, tier: SubscriptionTier) -> Team:
        """Upgrade team subscription tier."""
        team = self.get_team(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
        
        # Set limits based on tier
        tier_limits = {
            SubscriptionTier.FREE: (10, 5),
            SubscriptionTier.STARTER: (50, 10),
            SubscriptionTier.PROFESSIONAL: (200, 50),
            SubscriptionTier.ENTERPRISE: (float('inf'), float('inf'))
        }
        
        team.subscription_tier = tier
        team.max_repos, team.max_team_members = tier_limits[tier]
        team.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(team)
        return team
    
    def get_team_stats(self, team_id: str) -> dict:
        """Get team statistics."""
        team = self.get_team(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")
        
        return {
            "team_id": team.id,
            "name": team.name,
            "tier": team.subscription_tier.value,
            "member_count": len(team.users),
            "repo_count": len(team.repositories),
            "max_repos": team.max_repos,
            "max_members": team.max_team_members
        }


# ============================================================================
# User Management
# ============================================================================

class UserManager:
    """Manages user accounts and authentication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(
        self, 
        email: str, 
        username: str, 
        password: str,
        team_id: str,
        full_name: str = "",
        role: UserRole = UserRole.DEVELOPER
    ) -> User:
        """Create a new user."""
        if self.get_user_by_email(email):
            raise ValueError(f"User with email {email} already exists")
        
        if self.get_user_by_username(username):
            raise ValueError(f"Username {username} already taken")
        
        user = User(
            id=str(uuid.uuid4()),
            team_id=team_id,
            email=email,
            username=username,
            password_hash=self.hash_password(password),
            full_name=full_name,
            role=role
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        user.last_login = datetime.utcnow()
        self.db.commit()
        return user
    
    def change_role(self, user_id: str, new_role: UserRole, authorized_by: str) -> User:
        """Change user role (authorized action)."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check authorization (not enforced here, should be done by caller)
        user.role = new_role
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def deactivate_user(self, user_id: str) -> User:
        """Deactivate user account."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hash: str) -> bool:
        """Verify password against hash."""
        return hashlib.sha256(password.encode()).hexdigest() == hash


# ============================================================================
# API Key Management
# ============================================================================

class APIKeyManager:
    """Manages API keys for programmatic access."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_api_key(
        self, 
        user_id: str, 
        name: str,
        expires_in_days: int = 90
    ) -> tuple[str, APIKey]:
        """Create a new API key.
        
        Returns:
            Tuple of (plain_key, api_key_object)
            Note: Plain key is only shown once!
        """
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days)
        )
        
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        
        return plain_key, api_key
    
    def get_api_key(self, user_id: str, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        return self.db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
    
    def list_api_keys(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        return self.db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.is_active == True
        ).all()
    
    def validate_api_key(self, plain_key: str) -> Optional[APIKey]:
        """Validate and return API key object."""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        
        api_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if api_key and api_key.expires_at:
            if api_key.expires_at < datetime.utcnow():
                return None
        
        if api_key:
            api_key.last_used = datetime.utcnow()
            self.db.commit()
        
        return api_key
    
    def revoke_api_key(self, user_id: str, key_id: str):
        """Revoke an API key."""
        api_key = self.get_api_key(user_id, key_id)
        if not api_key:
            raise ValueError(f"API key {key_id} not found")
        
        api_key.is_active = False
        self.db.commit()


# ============================================================================
# RBAC (Role-Based Access Control)
# ============================================================================

class AccessController:
    """Manages access control and permissions."""
    
    # Permission mappings
    PERMISSIONS = {
        UserRole.ADMIN: [
            "create_team", "delete_team", "manage_users", "manage_settings",
            "create_scan", "view_findings", "create_patches", "approve_patches",
            "create_webhook", "manage_notifications", "export_reports", 
            "manage_api_keys", "view_audit_logs", "manage_subscription"
        ],
        UserRole.MANAGER: [
            "create_scan", "view_findings", "create_patches", "approve_patches",
            "manage_users_basic", "view_audit_logs", "create_webhook",
            "manage_notifications", "export_reports"
        ],
        UserRole.DEVELOPER: [
            "create_scan", "view_findings", "create_patches", "view_audit_logs"
        ],
        UserRole.VIEWER: [
            "view_findings"
        ]
    }
    
    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """Check if user has permission."""
        permissions = AccessController.PERMISSIONS.get(user.role, [])
        return permission in permissions
    
    @staticmethod
    def require_permission(user: User, permission: str):
        """Raise error if user lacks permission."""
        if not AccessController.has_permission(user, permission):
            raise PermissionError(
                f"User {user.email} (role: {user.role}) "
                f"does not have permission: {permission}"
            )
    
    @staticmethod
    def get_permissions(user: User) -> List[str]:
        """Get all permissions for a user."""
        return AccessController.PERMISSIONS.get(user.role, [])


# ============================================================================
# JWT Token Management
# ============================================================================

class TokenManager:
    """Manages JWT tokens for API authentication."""
    
    @staticmethod
    def create_token(user: User, expires_in_hours: int = 24) -> str:
        """Create a JWT token."""
        payload = {
            "user_id": user.id,
            "email": user.email,
            "team_id": user.team_id,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours)
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
