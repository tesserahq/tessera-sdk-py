"""
Custom exceptions for the Custos client.
"""

from .._base.exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)


class CustosError(TesseraError):
    pass


class CustosClientError(TesseraClientError):
    pass


class CustosServerError(TesseraServerError):
    pass


class CustosAuthenticationError(TesseraAuthenticationError):
    pass


class CustosNotFoundError(TesseraNotFoundError):
    pass


class CustosValidationError(TesseraValidationError):
    pass
