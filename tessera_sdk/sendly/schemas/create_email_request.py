from pydantic import BaseModel, Field
from typing import List, Dict, Any


class TemplateVariables(BaseModel):
    """Schema for template variables."""

    model_config = {"from_attributes": True}


class CreateEmailRequest(BaseModel):
    """Schema for send email request."""

    name: str
    """Name/identifier for the email."""

    project_id: str
    """Project identifier."""

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

    model_config = {"from_attributes": True}
