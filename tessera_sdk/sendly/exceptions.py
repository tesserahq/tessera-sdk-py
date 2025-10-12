"""
Custom exceptions for the Sendly client.
"""

from ..base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class SendlyError(TesseraError):
    """Base exception for all Sendly-related errors."""

    pass


class SendlyClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""

    pass


class SendlyServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""

    pass


class SendlyAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""

    pass


class SendlyNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""

    pass


class SendlyValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""

    pass
