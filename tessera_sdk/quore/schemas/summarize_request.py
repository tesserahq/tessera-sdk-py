from pydantic import BaseModel
from typing import Optional, Dict, Any


class SummarizeRequest(BaseModel):
    """Schema for summarize request."""

    prompt_id: str
    """ID of the prompt to use for summarization."""

    text: str
    """Text content to be summarized."""

    query: str
    """Query used for the summarization."""

    labels: Optional[Dict[str, Any]] = None
    """Optional labels/metadata for the summarization request."""

    class ConfigDict:
        """Pydantic model configuration."""

        from_attributes = True
