"""
Schemas for Looply contact endpoints.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ContactCreateRequest(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job: Optional[str] = None
    contact_type: Optional[str] = None
    phone_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job: Optional[str] = None
    contact_type: Optional[str] = None
    phone_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class Contact(BaseModel):
    id: UUID
    first_name: str
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job: Optional[str] = None
    contact_type: Optional[str] = None
    phone_type: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_by_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
