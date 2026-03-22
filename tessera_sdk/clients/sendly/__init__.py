"""
Sendly client module for email management.
"""

from .client import SendlyClient
from .schemas import CreateEmailRequest, CreateEmailResponse

__all__ = [
    "SendlyClient",
    "CreateEmailRequest",
    "CreateEmailResponse",
]
