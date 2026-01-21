from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserNeedsOnboarding(BaseModel):
    """Schema for user needs onboarding data."""

    needs_onboarding: bool
    """Whether the user needs onboarding."""

    external_id: str
    """External user ID from the authentication provider."""


class UserOnboard(BaseModel):
    """Schema for user onboarding data."""

    external_id: str
    """External user ID from the authentication provider."""

    id: Optional[UUID] = None
    """Internal user ID."""

    email: Optional[EmailStr] = None
    """User's email address."""

    first_name: str = ""
    """User's first name."""

    last_name: str = ""
    """User's last name."""

    avatar_url: Optional[str] = None
    """URL to the user's avatar image."""

    verified: bool = False
    """Whether the user is verified."""

    verified_at: Optional[datetime] = None
    """Timestamp when the user was verified."""

    service_account: Optional[bool] = None
    """Whether the user is a service account."""


class UserServiceInterface:
    """Interface for user service operations."""

    def onboard_user(self, user_data: UserOnboard):
        """
        Onboard a new user with the provided data.

        Args:
            user_data: UserOnboard object containing user information

        Returns:
            The onboarded user object
        """
        raise NotImplementedError("Subclasses must implement onboard_user method")

    def get_user_by_external_id(self, external_id: str):
        """
        Get a user by their external ID.

        Args:
            external_id: External user ID from the authentication provider

        Returns:
            User object if found, None otherwise
        """
        raise NotImplementedError(
            "Subclasses must implement get_user_by_external_id method"
        )
