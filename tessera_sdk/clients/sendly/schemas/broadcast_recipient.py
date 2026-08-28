from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional
from uuid import UUID


class BroadcastRecipient(BaseModel):
    """One recipient in a broadcast send."""

    email: EmailStr
    """Recipient email address. Required."""

    first_name: Optional[str] = None
    """Recipient first name, available as a template variable."""

    last_name: Optional[str] = None
    """Recipient last name, available as a template variable."""

    attributes: Dict[str, Any] = Field(default_factory=dict)
    """Arbitrary per-recipient personalization data, merged into template_variables."""

    client_reference_id: Optional[UUID] = None
    """Optional caller-owned id for correlating this recipient with its
    results later (see SendlyClient.list_broadcast_recipients) without
    matching on the mutable email address. Must be unique within one
    broadcast when supplied; reusing it in a different broadcast is fine."""
