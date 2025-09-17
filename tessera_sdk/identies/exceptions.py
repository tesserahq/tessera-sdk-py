"""
Custom exceptions for the Identies client.
"""

from ..base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class IdentiesError(TesseraError):
    """Base exception for all Identies-related errors."""

    pass


class IdentiesClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""

    pass


class IdentiesServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""

    pass


class IdentiesAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""

    pass


class IdentiesNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""

    pass


class IdentiesValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""

    pass
