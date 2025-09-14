from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserResponse(BaseModel):
    """Schema for user data returned in API responses, prioritizing avatar_asset_id over avatar_url."""

    id: UUID
    """Unique identifier for the user in the database."""

    email: Optional[EmailStr] = None
    """User's email address. Must be a valid email format."""

    username: Optional[str] = None
    """User's unique username. Can be used for login or display."""

    avatar_url: Optional[str] = None
    """URL to the user's profile picture or avatar. Returns avatar_asset_id if present, otherwise avatar_url."""

    avatar_asset_id: Optional[str] = None
    """Asset ID of the user's profile picture or avatar."""

    first_name: str
    """User's first name. Required field."""

    last_name: str
    """User's last name. Required field."""

    provider: Optional[str] = None
    """Authentication provider (e.g., 'google', 'github', etc.) if user signed up via OAuth."""

    confirmed_at: Optional[datetime] = None
    """Timestamp when the user confirmed their email address."""

    verified: bool = False
    """Whether the user's account has been verified. Defaults to False."""

    verified_at: Optional[datetime] = None
    """Timestamp when the user's account was verified."""

    theme_preference: Optional[str] = "system"
    """User's theme preference. Can be 'system', 'dark', or 'light'. Defaults to 'system'."""

    created_at: datetime
    """Timestamp when the user record was created."""

    updated_at: datetime
    """Timestamp when the user record was last updated."""

    avatar_url: Optional[str] = None
    """URL to the user's profile picture or avatar."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
