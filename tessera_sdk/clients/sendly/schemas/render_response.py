from pydantic import BaseModel


class RenderResponse(BaseModel):
    """Schema for the rendered preview of a piece of content."""

    html: str
    """The body, wrapped in the layout when one was given."""

    subject: str
    """The rendered subject line."""
