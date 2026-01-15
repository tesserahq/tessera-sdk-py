from datetime import datetime
from typing import Any, Dict, Optional, Union, List
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID, uuid4

from tessera_sdk.config import get_settings


class Event(BaseModel):
    """
    CloudEvents-compliant event schema following the CloudEvents specification.

    This implements the CloudEvents v1.0 specification for describing event data
    in a common way across services and platforms.

    Reference: https://cloudevents.io/
    """

    # Required attributes
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the event",
    )
    source: str = Field(
        ...,
        description="URI-reference that identifies the context in which an event happened",
    )
    spec_version: str = Field(
        default="1.0", description="Version of the CloudEvents specification"
    )
    event_type: str = Field(..., description="Type of occurrence which has happened")

    # Optional attributes
    data_content_type: Optional[str] = Field(
        default="application/json", description="Content type of data value"
    )
    dataschema: Optional[str] = Field(
        default=None, description="URI of the schema that data adheres to"
    )
    subject: Optional[str] = Field(
        default=None,
        description="Describes the subject of the event in the context of the event producer",
    )
    time: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of when the occurrence happened",
    )
    event_data: Optional[Union[Dict[str, Any], str, bytes]] = Field(
        default=None, description="The event payload"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID associated with the event (extension attribute)",
    )
    labels: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Labels associated with the event (extension attribute)",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags associated with the event (extension attribute)",
    )
    project_id: Optional[UUID] = Field(
        default=None,
        description="Project UUID associated with the event (extension attribute)",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v):
        """Validate that source is a valid URI-reference."""
        if not v or not isinstance(v, str):
            raise ValueError("Source must be a non-empty string")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_type(cls, v):
        """Validate that type is a valid event type."""
        if not v or not isinstance(v, str):
            raise ValueError("Type must be a non-empty string")
        return v

    @field_validator("spec_version")
    @classmethod
    def validate_spec_version(cls, v):
        """Validate spec_version."""
        if v != "1.0":
            raise ValueError("Only CloudEvents spec_version 1.0 is supported")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v):
        """Ensure time is in UTC."""
        if v and v.tzinfo is None:
            # If no timezone info, assume UTC
            return v.replace(tzinfo=None)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "/api/accounts/123",
                "spec_version": "1.0",
                "type": "com.mylinden.family.account.created",
                "data_content_type": "application/json",
                "time": "2024-01-15T10:30:00Z",
                "data": {
                    "account_id": "123",
                    "name": "Example Account",
                    "email": "account@example.com",
                },
            }
        }
    )


def event_type(type: str) -> str:
    """Get the event type."""
    settings = get_settings()
    return f"{settings.event_type_prefix}.{type}"


def event_source(source: str = "") -> str:
    """Get the event source."""
    settings = get_settings()
    return f"/{settings.event_source_prefix}{source}"
