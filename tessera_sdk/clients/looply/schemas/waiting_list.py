"""
Schemas for Looply waiting list endpoints.
"""

from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class WaitingListCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class WaitingListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class WaitingList(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_by_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AddWaitingListMembersRequest(BaseModel):
    contact_ids: list[UUID]
    status: Optional[str] = "pending"

    model_config = {"from_attributes": True}


class WaitingListMemberCountResponse(BaseModel):
    waiting_list_id: UUID
    count: int
    status: Optional[str] = None

    model_config = {"from_attributes": True}
