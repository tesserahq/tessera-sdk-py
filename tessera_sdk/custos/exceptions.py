"""
Custom exceptions for the Custos client.
"""

from ..base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class CustosError(TesseraError):
    """Base exception for all Custos-related errors."""

    pass


class CustosClientError(TesseraClientError):
    """Exception raised for client-side errors (4xx status codes)."""

    pass


class CustosServerError(TesseraServerError):
    """Exception raised for server-side errors (5xx status codes)."""

    pass


class CustosAuthenticationError(TesseraAuthenticationError):
    """Exception raised for authentication errors (401 status code)."""

    pass


class CustosNotFoundError(TesseraNotFoundError):
    """Exception raised when a resource is not found (404 status code)."""

    pass


class CustosValidationError(TesseraValidationError):
    """Exception raised for validation errors (400 status code)."""

    pass
