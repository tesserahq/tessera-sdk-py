"""
Custos Client - A Python client for the Custos API.

This package provides a convenient interface for interacting with the Custos API,
including authorization functionality.
"""

from .client import CustosClient
from .exceptions import (
    CustosError,
    CustosClientError,
    CustosServerError,
    CustosAuthenticationError,
    CustosNotFoundError,
    CustosValidationError,
)

__all__ = [
    "CustosClient",
    "CustosError",
    "CustosClientError",
    "CustosServerError",
    "CustosAuthenticationError",
    "CustosNotFoundError",
    "CustosValidationError",
]
