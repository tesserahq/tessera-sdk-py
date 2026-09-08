"""
Tessera SDK for Python

A Python SDK for Tessera with Identies integration, authentication middleware, and user onboarding.
"""

from .clients._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraNotFoundError,
    TesseraServerError,
    TesseraValidationError,
)
from .clients.custos import CustosClient
from .clients.identies import IdentiesClient
from .clients.looply import LooplyClient
from .clients.quore import QuoreClient
from .clients.sendly import SendlyClient
from .clients.togly import ToglyClient
from .clients.vaulta import VaultaClient

__version__ = "0.1.0"

__all__ = [
    "CustosClient",
    "IdentiesClient",
    "LooplyClient",
    "QuoreClient",
    "SendlyClient",
    "TesseraAuthenticationError",
    "TesseraClientError",
    "TesseraError",
    "TesseraNotFoundError",
    "TesseraServerError",
    "TesseraValidationError",
    "ToglyClient",
    "VaultaClient",
]
