"""
Tessera SDK for Python

A Python SDK for Tessera with Identies integration, authentication middleware, and user onboarding.
"""

from .clients.identies import IdentiesClient
from .clients.quore import QuoreClient
from .clients.vaulta import VaultaClient
from .clients.sendly import SendlyClient
from .clients.custos import CustosClient
from .clients.looply import LooplyClient
from .clients._base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "IdentiesClient",
    "QuoreClient",
    "VaultaClient",
    "SendlyClient",
    "CustosClient",
    "LooplyClient",
    "TesseraError",
    "TesseraClientError",
    "TesseraServerError",
    "TesseraAuthenticationError",
    "TesseraNotFoundError",
    "TesseraValidationError",
]
