"""Schema for external account API responses and link token requests/responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ExternalAccountResponse(BaseModel):
    """External account as returned by the API."""

    id: UUID
    user_id: UUID
    platform: str
    external_id: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExternalAccountPageResponse(BaseModel):
    """Paginated list of external accounts."""

    items: list[ExternalAccountResponse]
    total: int
    page: int
    size: int
    pages: int


class LinkTokenResponse(BaseModel):
    """Response after creating a link token."""

    token: str
    expires_at: datetime

    model_config = {"from_attributes": True}
