"""
Tessera SDK for Python

A Python SDK for Tessera with Identies integration, authentication middleware, and user onboarding.
"""

from .identies import IdentiesClient
from .quore import QuoreClient
from .vaulta import VaultaClient
from .sendly import SendlyClient

__version__ = "0.1.0"

__all__ = [
    "IdentiesClient",
    "QuoreClient",
    "VaultaClient",
    "SendlyClient",
]
