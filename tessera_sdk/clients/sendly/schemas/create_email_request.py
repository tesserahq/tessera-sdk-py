from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
from uuid import UUID


class Attachment(BaseModel):
    """Email attachment."""

    filename: str
    content_bytes_b64: str
    mime_type: str = "application/octet-stream"


class CreateEmailRequest(BaseModel):
    """Schema for creating an email."""

    project_id: Optional[UUID] = None
    """Project identifier."""

    from_email: Optional[EmailStr] = None
    """Sender email address. Falls back to Sendly's configured default if not provided."""

    subject: str
    """Email subject line."""

    html: Optional[str] = None
    """HTML content of the email."""

    text: Optional[str] = None
    """Plain text content of the email."""

    to: List[EmailStr]
    """List of recipient email addresses."""

    cc: List[EmailStr] = Field(default_factory=list)
    """CC recipients."""

    bcc: List[EmailStr] = Field(default_factory=list)
    """BCC recipients."""

    attachments: List[Attachment] = Field(default_factory=list)
    """File attachments."""

    template_id: Optional[str] = None
    """Template identifier for templated emails."""

    template_variables: Dict[str, Any] = Field(default_factory=dict)
    """Variables to substitute in the email template."""

    custom_headers: Dict[str, str] = Field(default_factory=dict)
    """Custom email headers."""

    priority: Optional[int] = None
    """Email priority level."""

    idempotency_key: Optional[str] = None
    """Optional key to deduplicate client retries."""

    model_config = {"from_attributes": True}
