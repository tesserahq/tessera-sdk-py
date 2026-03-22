from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from .user_response import UserResponse


class IntrospectResponse(BaseModel):
    """Schema for API key introspection response."""

    active: bool
    """Whether the API key is active (valid, not revoked, not expired)."""

    user: Optional[UserResponse] = None
    """User object associated with the API key. Only present if active is True."""

    user_id: Optional[UUID] = None
    """User ID associated with the API key. Only present if active is True."""

    key_id: Optional[str] = None
    """Public key ID. Only present if active is True."""

    scopes: Optional[list[str]] = None
    """Scopes/permissions for the API key. Only present if active is True."""

    expires_at: Optional[datetime] = None
    """Expiration date of the API key. Only present if active is True."""

    model_config = {"from_attributes": True}
