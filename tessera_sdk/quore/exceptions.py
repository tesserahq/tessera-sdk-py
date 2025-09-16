"""
Custom exceptions for the Quore client.
"""

from ..base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class QuoreError(TesseraError):
    """Base exception for all Quore-related errors."""
    pass


class QuoreClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""
    pass


class QuoreServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""
    pass


class QuoreAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""
    pass


class QuoreNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""
    pass


class QuoreValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""
    pass
