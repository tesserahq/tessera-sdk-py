"""
Schemas for Looply contact interaction endpoints.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from .contact import Contact


class ContactInteractionCreateRequest(BaseModel):
    note: Optional[str] = None
    interaction_timestamp: Optional[datetime] = None
    action: Optional[str] = None
    custom_action_description: Optional[str] = None
    action_timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactInteractionUpdate(BaseModel):
    note: Optional[str] = None
    interaction_timestamp: Optional[datetime] = None
    action: Optional[str] = None
    custom_action_description: Optional[str] = None
    action_timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ContactInteraction(BaseModel):
    id: UUID
    contact_id: UUID
    note: Optional[str] = None
    interaction_timestamp: Optional[datetime] = None
    action: Optional[str] = None
    custom_action_description: Optional[str] = None
    action_timestamp: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    contact: Optional[Contact] = None

    model_config = {"from_attributes": True}
