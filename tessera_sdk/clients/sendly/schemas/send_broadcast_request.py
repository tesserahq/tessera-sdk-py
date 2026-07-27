from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
from uuid import UUID

from .broadcast_recipient import BroadcastRecipient


class Attachment(BaseModel):
    """Email attachment."""

    filename: str
    content_bytes_b64: str
    mime_type: str = "application/octet-stream"


class SendBroadcastRequest(BaseModel):
    """Schema for sending a broadcast to a list of recipients.

    Reuses the same content options CreateEmailRequest already supports;
    batch_id, cc, bcc, and priority are intentionally absent — Sendly
    generates batch_id server-side, and cc/bcc have no coherent
    per-recipient meaning for a fan-out send.
    """

    project_id: UUID
    """Project identifier."""

    from_email: Optional[EmailStr] = None
    """Sender email address. Falls back to the template's default if not provided."""

    subject: Optional[str] = None
    """Email subject line. Required unless using a template with its own subject."""

    html: Optional[str] = None
    """HTML content of the email. Mutually exclusive with template_id/template_alias."""

    text: Optional[str] = None
    """Plain text content of the email."""

    attachments: List[Attachment] = Field(default_factory=list)
    """File attachments, shared across every recipient."""

    template_id: Optional[UUID] = None
    """Template identifier for templated broadcasts."""

    template_alias: Optional[str] = None
    """Template alias for templated broadcasts."""

    template_variables: Dict[str, Any] = Field(default_factory=dict)
    """Shared template variables, merged with each recipient's own attributes."""

    custom_headers: Dict[str, str] = Field(default_factory=dict)
    """Custom email headers, shared across every recipient."""

    idempotency_key: Optional[str] = None
    """Optional key to deduplicate client retries; a repeated key with different
    content returns a conflict rather than sending twice."""

    tags: Optional[List[str]] = None
    """Free-form caller-supplied tags for campaign/filtering purposes."""

    metadata: Optional[Dict[str, Any]] = None
    """Free-form caller-supplied metadata."""

    recipients: List[BroadcastRecipient] = Field(min_length=1)
    """The recipients to send to. Must be non-empty."""
