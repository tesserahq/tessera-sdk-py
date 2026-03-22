"""
Schemas for Looply contact list endpoints.
"""

from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from .contact import Contact


class ContactListCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

    model_config = {"from_attributes": True}


class ContactListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

    model_config = {"from_attributes": True}


class ContactList(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_public: bool = False
    created_by_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AddMembersRequest(BaseModel):
    contact_ids: list[UUID]

    model_config = {"from_attributes": True}


class ListMembersResponse(BaseModel):
    contact_list_id: UUID
    members: list[Contact]
    total: int

    model_config = {"from_attributes": True}


class MemberCountResponse(BaseModel):
    contact_list_id: UUID
    count: int

    model_config = {"from_attributes": True}


class SubscribeResponse(BaseModel):
    contact_list_id: UUID
    subscribed: bool
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class ContactListSubscription(BaseModel):
    id: Optional[UUID] = None
    contact_list_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    contact_list: Optional[ContactList] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
