from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AssetState(str, Enum):
    """Enumeration of valid asset states."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetBase(BaseModel):
    """Base file model containing common file attributes."""

    name: str
    """Human readable name for the file."""
    
    filename: str
    """Original filename."""
    
    mime_type: str
    """File type (e.g., application/pdf, image/jpeg)."""
    
    size: int
    """File size in bytes."""
    
    labels: Dict[str, Any] = Field(default_factory=dict)
    """Dictionary of labels."""
    
    state: str
    """Current state of the asset."""
    
    state_message: Optional[str] = None
    """Optional message describing the current state."""

    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        valid_states = {state.value for state in AssetState}
        if v.lower() not in valid_states:
            raise ValueError(
                f'Invalid state. Must be one of: {", ".join(valid_states)}'
            )
        return v.lower()


class AssetResponse(AssetBase):
    """Schema for asset data returned in API responses."""

    id: str
    """Unique identifier for the asset."""

    created_at: Optional[datetime] = None
    """Timestamp when the asset was created."""

    updated_at: Optional[datetime] = None
    """Timestamp when the asset was last updated."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
