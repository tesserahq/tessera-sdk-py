from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class SummarizeResponse(BaseModel):
    """Schema for summarize response."""

    summary: str
    """The generated summary text."""

    prompt_id: Optional[str] = None
    """ID of the prompt used for summarization."""

    labels: Optional[Dict[str, Any]] = None
    """Labels/metadata associated with the summarization."""

    created_at: Optional[datetime] = None
    """Timestamp when the summary was created."""

    tokens_used: Optional[int] = None
    """Number of tokens used for the summarization."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
