from pydantic import BaseModel
from typing import Optional


class AuthorizeResponse(BaseModel):
    """Schema for authorization response."""

    allowed: bool
    """Whether the authorization was granted."""

    user_id: str
    """User identifier."""

    action: str
    """Action to authorize (e.g., 'create', 'read', 'update', 'delete')."""

    resource: str
    """Resource type to authorize (e.g., 'account', 'document')."""

    domain: str
    """Domain identifier (e.g., 'account:1234')."""

    reason: Optional[str] = None
    """Optional message from the authorization service."""

    model_config = {"from_attributes": True}
