"""
Sendly schemas module.
"""

from .create_email_request import CreateEmailRequest, TemplateVariables
from .create_email_response import CreateEmailResponse

__all__ = [
    "CreateEmailRequest",
    "TemplateVariables",
    "CreateEmailResponse",
]
