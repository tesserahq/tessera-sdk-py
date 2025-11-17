"""
Custom exceptions for the Vaulta client.
"""

from ..base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class VaultaError(TesseraError):
    """Base exception for all Vaulta-related errors."""

    pass


class VaultaClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""

    pass


class VaultaServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""

    pass


class VaultaAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""

    pass


class VaultaNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""

    pass


class VaultaValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""

    pass
