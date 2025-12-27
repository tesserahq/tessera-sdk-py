from pydantic import BaseModel, Field
from typing import Dict, Any


class CreateBindingRequest(BaseModel):
    """Schema for creating a role binding."""

    user_id: str
    """User identifier to bind to the role."""

    domain: str
    """Domain identifier for the binding."""

    domain_metadata: Dict[str, Any] = Field(default_factory=dict)
    """Metadata for the domain."""

    model_config = {"from_attributes": True}


class DeleteBindingRequest(BaseModel):
    """Schema for deleting a role binding."""

    user_id: str
    """User identifier to unbind from the role."""

    domain: str
    """Domain identifier for the binding."""

    model_config = {"from_attributes": True}
