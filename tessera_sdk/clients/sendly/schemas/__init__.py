"""
Sendly schemas module.
"""

from .create_email_request import CreateEmailRequest
from .create_email_response import CreateEmailResponse
from .broadcast_recipient import BroadcastRecipient
from .send_broadcast_request import SendBroadcastRequest
from .send_broadcast_response import SendBroadcastResponse
from .get_broadcast_response import GetBroadcastResponse

__all__ = [
    "CreateEmailRequest",
    "CreateEmailResponse",
    "BroadcastRecipient",
    "SendBroadcastRequest",
    "SendBroadcastResponse",
    "GetBroadcastResponse",
]
