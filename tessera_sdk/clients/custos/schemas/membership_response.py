from pydantic import BaseModel
from typing import Optional, Dict, Any


class MembershipResponse(BaseModel):
    """Schema for membership response."""

    membership_id: Optional[str] = None
    """Membership identifier."""

    role_id: Optional[str] = None
    """Role identifier."""

    user_id: Optional[str] = None
    """User identifier."""

    subject_id: Optional[str] = None
    """Subject identifier."""

    resource: Optional[str] = None
    """Resource identifier."""

    domain: Optional[str] = None
    """Domain identifier."""

    domain_metadata: Optional[Dict[str, Any]] = None
    """Metadata for the domain."""

    created_at: Optional[str] = None
    """Timestamp when the membership was created."""

    model_config = {"from_attributes": True}
