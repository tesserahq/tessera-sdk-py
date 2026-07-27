"""
Sendly client module for email management.
"""

from .client import SendlyClient
from .schemas import (
    CreateEmailRequest,
    CreateEmailResponse,
    BroadcastRecipient,
    SendBroadcastRequest,
    SendBroadcastResponse,
    GetBroadcastResponse,
)

__all__ = [
    "SendlyClient",
    "CreateEmailRequest",
    "CreateEmailResponse",
    "BroadcastRecipient",
    "SendBroadcastRequest",
    "SendBroadcastResponse",
    "GetBroadcastResponse",
]
