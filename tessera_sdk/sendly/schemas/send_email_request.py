from pydantic import BaseModel, Field
from typing import List, Dict, Any


class TemplateVariables(BaseModel):
    """Schema for template variables."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        extra = "allow"


class SendEmailRequest(BaseModel):
    """Schema for send email request."""

    name: str
    """Name/identifier for the email."""

    tenant_id: str
    """Tenant identifier."""

    from_email: str
    """Sender email address."""

    subject: str
    """Email subject line."""

    html: str
    """HTML content of the email."""

    to: List[str]
    """List of recipient email addresses."""

    template_variables: Dict[str, Any] = Field(default_factory=dict)
    """Variables to be replaced in the email template."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
