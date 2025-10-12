from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SendEmailResponse(BaseModel):
    """Schema for send email response."""

    from_email: str
    """Sender email address."""

    to_email: str
    """Recipient email address."""

    subject: str
    """Email subject line."""

    body: str
    """Processed email body with template variables replaced."""

    status: str
    """Status of the email (e.g., 'sent', 'failed')."""

    provider_id: str
    """Provider identifier."""

    provider_message_id: str
    """Provider's message identifier."""

    tenant_id: str
    """Tenant identifier."""

    id: str
    """Unique identifier for the email record."""

    sent_at: Optional[datetime] = None
    """Timestamp when the email was sent."""

    error_message: Optional[str] = None
    """Error message if the email failed to send."""

    created_at: Optional[datetime] = None
    """Timestamp when the record was created."""

    updated_at: Optional[datetime] = None
    """Timestamp when the record was last updated."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
