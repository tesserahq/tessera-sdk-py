from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import UUID


class RenderRequest(BaseModel):
    """Schema for previewing content exactly as an inline send renders it."""

    html: str
    """HTML body to render (Mako, with template_variables)."""

    subject: str = ""
    """Subject line to render (Mako, with template_variables)."""

    layout_id: Optional[UUID] = None
    """Layout to wrap the body in, passed to it as `content`."""

    layout_alias: Optional[str] = None
    """Layout alias, as an alternative to layout_id (layout_id wins if both
    are given)."""

    template_variables: Dict[str, Any] = Field(default_factory=dict)
    """Variables available to the body, the layout, and the subject."""
