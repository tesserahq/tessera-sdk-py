from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class TemplateResponse(BaseModel):
    """A Sendly email template."""

    id: UUID
    alias: str
    name: Optional[str] = None
    subject: str
    """Subject line (Mako). A templated send always uses this, not the
    request's subject."""

    html: str
    """Body (Mako), wrapped in the template's layout when it has one."""

    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    layout_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
