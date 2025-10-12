"""
Sendly schemas module.
"""

from .send_email_request import SendEmailRequest, TemplateVariables
from .send_email_response import SendEmailResponse

__all__ = [
    "SendEmailRequest",
    "TemplateVariables",
    "SendEmailResponse",
]
