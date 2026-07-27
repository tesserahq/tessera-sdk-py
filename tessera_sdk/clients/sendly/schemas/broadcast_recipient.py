from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional


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
