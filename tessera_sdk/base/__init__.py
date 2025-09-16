"""
Base classes and utilities for the Tessera SDK.
"""

from .client import BaseClient
from .exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)

__all__ = [
    "BaseClient",
    "TesseraError",
    "TesseraClientError",
    "TesseraServerError",
    "TesseraAuthenticationError",
    "TesseraNotFoundError",
    "TesseraValidationError",
]
