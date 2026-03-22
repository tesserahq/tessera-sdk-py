from pydantic import BaseModel, Field
from typing import Dict, Any


class CreateMembershipRequest(BaseModel):
    """Schema for creating a role membership."""

    user_id: str
    """User identifier to add to the role."""

    domain: str
    """Domain identifier for the membership."""

    domain_metadata: Dict[str, Any] = Field(default_factory=dict)
    """Metadata for the domain."""

    model_config = {"from_attributes": True}


class DeleteMembershipRequest(BaseModel):
    """Schema for deleting a role membership."""

    user_id: str
    """User identifier to remove from the role."""

    domain: str
    """Domain identifier for the membership."""

    model_config = {"from_attributes": True}
