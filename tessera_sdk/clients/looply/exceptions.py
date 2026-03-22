"""
Custom exceptions for the Looply client.
"""

from .._base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class LooplyError(TesseraError):
    """Base exception for all Looply-related errors."""

    pass


class LooplyClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""

    pass


class LooplyServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""

    pass


class LooplyAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""

    pass


class LooplyNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""

    pass


class LooplyValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""

    pass
